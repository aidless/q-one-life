"""Explicit model fixtures test automatic behavior; live inference is recorded separately."""
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from qone_agent.runtime import ProviderError, RunResult
from qone_core.ledger import Ledger
from qone_life.backup import LEGACY_TABLES
from qone_life.plan_runtime import PlanResult, generate_plan, validate_plan
from qone_life.planner import Planner
from qone_life.repository import Repository
from qone_life.web import DEFAULTS, create_app

GOAL = {"title": "完成Python入门项目", "success_criterion": "保存可运行的命令行工具", "domain": "learning", "priority": 5}
HEADERS = {"X-QOne-Client": "web"}


def fixture_plan(snapshot, config):
    c = snapshot["candidates"][0]
    return PlanResult([{"candidate_id": c["id"], "title": "完成并保存一个Python小练习", "reason": "为已有项目目标验证一个小步骤，仍需执行后回看",
                        "minutes": min(25, snapshot["available_minutes"])}], "fixture", "explicit-test-fixture")


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Repository(self.temp.name)
        self.ledger = Ledger(Path(self.temp.name) / "decisions.jsonl")
        self.config = DEFAULTS.copy()
        self.calls = []
        def runner(snapshot, config):
            self.calls.append(snapshot)
            return fixture_plan(snapshot, config)
        self.planner = Planner(self.repo, self.ledger, lambda: self.config.copy(), threading.Lock(), runner)

    def test_no_goal_prompts_setup_without_calling_a_model(self):
        self.planner.tick()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.planner.state()["items"], [])
        self.assertEqual(self.repo.all("suggestions"), [])

    def test_goal_alone_generates_action_without_decision_or_baseline(self):
        self.repo.goal(GOAL)
        self.planner.tick()
        state = self.planner.state()
        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["items"][0]["source"], "fixture:explicit-test-fixture")
        self.assertEqual(len(self.ledger.events()), 0)
        self.assertEqual(self.repo.all("tasks"), [])
        self.assertEqual(self.repo.all("runs")[0]["purpose"], "automatic_recommendation")

    def test_unchanged_input_is_cached_and_changes_trigger_another_plan(self):
        goal = self.repo.goal(GOAL)
        self.planner.tick()
        for _ in range(3):
            self.planner.state()
            self.planner.tick()
        self.assertEqual(len(self.calls), 1)
        self.repo.goal({"priority": 2}, goal["id"])
        self.planner.tick()
        self.assertEqual(len(self.calls), 2)

    def test_acceptance_is_required_and_does_not_duplicate_or_recommend_same_action(self):
        self.repo.goal(GOAL)
        self.planner.tick()
        card = self.planner.state()["items"][0]
        self.assertFalse(self.repo.all("tasks"))
        self.planner.feedback(card["id"], "accept")
        task = self.repo.all("tasks")[0]
        self.assertFalse(task["done"])
        self.assertEqual(task["title"], card["title"])
        self.assertEqual(self.planner.state()["available_minutes"], 65)
        self.assertEqual(self.planner.state()["items"], [])
        with self.assertRaises(ValueError):
            self.planner.feedback(card["id"], "accept")
        self.assertEqual(len(self.repo.all("tasks")), 1)

    def test_dismissal_survives_restart_for_the_day(self):
        self.repo.goal(GOAL)
        self.planner.tick()
        self.planner.feedback(self.planner.state()["items"][0]["id"], "dismiss")
        restarted = Planner(Repository(self.temp.name), self.ledger, lambda: self.config.copy(), threading.Lock())
        self.assertEqual(restarted.state()["items"], [])
        self.assertEqual(self.repo.all("tasks"), [])

    def test_changed_input_discards_an_inflight_old_result(self):
        goal = self.repo.goal(GOAL)
        def change_during_inference(snapshot, config):
            self.repo.goal({"status": "completed"}, goal["id"])
            return fixture_plan(snapshot, config)
        self.planner.runner = change_during_inference
        self.planner.tick()
        self.assertEqual(self.planner.state()["items"], [])
        self.assertEqual(self.repo.all("runs")[0]["status"], "discarded")
        self.assertEqual(self.planner.state()["status"], "idle")

    def test_model_failure_keeps_transparent_rules_and_backs_off(self):
        self.repo.goal(GOAL)
        def fail(snapshot, config):
            self.calls.append(snapshot)
            raise ProviderError("连接失败")
        self.planner.runner = fail
        self.planner.tick()
        self.planner.tick()
        self.assertEqual(len(self.calls), 1)
        state = self.planner.state()
        self.assertEqual(state["status"], "rules")
        self.assertEqual(state["items"][0]["source"], "rules")
        self.assertEqual(state["error"], "连接失败")

    def test_paused_or_busy_planner_does_not_call_model(self):
        self.repo.goal(GOAL)
        self.config["auto_recommend_enabled"] = False
        self.planner.tick()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.planner.state()["items"], [])
        self.config["auto_recommend_enabled"] = True
        self.planner.model_lock.acquire()
        try:
            self.planner.tick()
            self.assertEqual(self.calls, [])
        finally:
            self.planner.model_lock.release()
        self.planner.tick()
        self.assertEqual(len(self.calls), 1)

    def test_snapshot_excludes_credentials_and_raw_observation_notes(self):
        self.repo.goal(GOAL)
        self.config["cloud_key"] = "private-api-key"
        metric = self.repo.metric({"name": "专注分钟", "domain": "learning"})
        self.repo.observation({"metric_id": metric["id"], "value": 5, "note": "private-note"})
        encoded = json.dumps(self.planner.snapshot(), ensure_ascii=False)
        self.assertNotIn("private-api-key", encoded)
        self.assertNotIn("private-note", encoded)
        self.assertIn("专注分钟", encoded)

    def test_unknown_ids_duplicates_and_over_budget_are_rejected(self):
        self.repo.goal(GOAL)
        snapshot = self.planner.snapshot()
        item = fixture_plan(snapshot, self.config).items[0]
        for items in ([item | {"candidate_id": "invented"}], [item, item], [item | {"minutes": 91}], [item | {"minutes": True}]):
            with self.subTest(items=items), self.assertRaises(ProviderError):
                validate_plan({"items": items}, snapshot)

    def test_local_ollama_contract_and_remote_refusal(self):
        self.repo.goal(GOAL)
        snapshot = self.planner.snapshot()
        calls = []
        def handler(request):
            body = json.loads(request.content)
            calls.append(body)
            self.assertFalse(body["stream"])
            return httpx.Response(200, json={"message": {"content": json.dumps({"items": fixture_plan(snapshot, self.config).items})}})
        transport = httpx.MockTransport(handler)
        result = generate_plan(snapshot, self.config, transport=transport)
        self.assertEqual(result.provider, "ollama")
        with self.assertRaises(ProviderError):
            generate_plan(snapshot, self.config | {"ollama_url": "https://remote.invalid"}, transport=transport)
        self.assertEqual(len(calls), 1)

    def test_laya_uses_real_adapter_contract_and_explicit_defer_alternative(self):
        self.repo.goal(GOAL)
        snapshot = self.planner.snapshot()
        selected = snapshot["candidates"][0]["id"]
        with patch("qone_life.plan_runtime.run_model", return_value=RunResult(
                recommendation={"option_id": selected}, model="test-laya")) as adapter:
            result = generate_plan(snapshot, self.config | {"auto_recommend_provider": "laya"})
        self.assertEqual(result.provider, "laya")
        self.assertEqual(len(adapter.call_args.args[0]["options"]), 2)

    def test_daily_rollover_restores_eligibility(self):
        self.repo.goal(GOAL)
        self.planner.tick()
        self.planner.feedback(self.planner.state()["items"][0]["id"], "dismiss")
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        class Tomorrow(datetime):
            @classmethod
            def now(cls, tz=None):
                return tomorrow.astimezone(tz)
        with patch("qone_life.planner.datetime", Tomorrow):
            self.assertTrue(self.planner.state()["items"])

    def test_background_lifecycle_generates_after_save_without_recommendation_request(self):
        called = threading.Event()
        def runner(snapshot, config):
            called.set()
            return fixture_plan(snapshot, config)
        app = create_app(self.temp.name, plan_runner=runner)
        with TestClient(app, base_url="http://localhost", headers=HEADERS) as client:
            response = client.post("/api/goals", json=GOAL)
            self.assertEqual(response.status_code, 201)
            self.assertTrue(called.wait(3), "background inference was not triggered by goal save")
            # Join a notification cycle; this is observation, not an explicit model request.
            with app.state.planner.lock:
                pass
            state = client.get("/api/planner").json()
            self.assertTrue(state["items"])
        self.assertFalse(app.state.planner.thread.is_alive())

    def test_v2_backup_roundtrip_and_legacy_v1_restore(self):
        app = create_app(self.temp.name)
        client = TestClient(app, base_url="http://localhost", headers=HEADERS)
        self.addCleanup(client.close)
        self.assertEqual(client.post("/api/goals", json=GOAL).status_code, 201)
        client.get("/api/bootstrap")  # Materialize the honest rules feed.
        backup = client.get("/api/backup").json()
        self.assertEqual(backup["format"], "q-one-backup-v2")
        with tempfile.TemporaryDirectory() as folder:
            other = TestClient(create_app(folder), base_url="http://localhost", headers=HEADERS)
            self.addCleanup(other.close)
            self.assertEqual(other.post("/api/restore", json=backup).status_code, 200)
            self.assertEqual(len(other.get("/api/bootstrap").json()["goals"]), 1)
        legacy = backup | {"format": "q-one-backup-v1", "tables": {n: backup["tables"][n] for n in LEGACY_TABLES}}
        with tempfile.TemporaryDirectory() as folder:
            other = TestClient(create_app(folder), base_url="http://localhost", headers=HEADERS)
            self.addCleanup(other.close)
            self.assertEqual(other.post("/api/restore", json=legacy).status_code, 200)

    def test_completed_action_unlocks_next_step_without_reusing_the_task(self):
        self.repo.goal(GOAL)
        self.planner.tick()
        first = self.planner.state()["items"][0]
        self.planner.feedback(first["id"], "accept", first["proposal_sha256"])
        task = self.repo.all("tasks")[0]
        self.repo.put("tasks", task | {"done": True})
        self.planner.tick()
        second = self.planner.state()["items"][0]
        self.assertNotEqual(first["revision"], second["revision"])
        self.assertEqual(self.calls[-1]["recent_completed_actions"][0]["title"], task["title"])
        self.planner.feedback(second["id"], "accept", second["proposal_sha256"])
        self.assertEqual(len(self.repo.all("tasks")), 2)
        self.assertEqual(self.planner.state()["available_minutes"], 40)

    def test_changed_proposal_cannot_be_accepted_using_the_old_confirmation(self):
        self.repo.goal(GOAL)
        rules = self.planner.state()["items"][0]
        self.planner.tick()
        with self.assertRaisesRegex(ValueError, "已更新"):
            self.planner.feedback(rules["id"], "accept", rules["proposal_sha256"])
        self.assertEqual(self.repo.all("tasks"), [])

    def test_configuration_change_discards_the_old_model_result(self):
        self.repo.goal(GOAL)
        def change_config(snapshot, config):
            self.config["ollama_model"] = "changed-model"
            return fixture_plan(snapshot, config)
        self.planner.runner = change_config
        self.planner.tick()
        self.assertEqual(self.repo.all("runs")[0]["status"], "discarded")
