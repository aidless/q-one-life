"""Application acceptance with an explicitly injected model fixture, never a live-model claim."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi.testclient import TestClient
from qone_agent.runtime import ProviderError, RunResult
from qone_life.web import create_app

HEADERS = {"X-QOne-Client": "web"}
DECISION = {"question": "今晚先完成练习还是阅读？", "domain": "learning", "success_criterion": "交付一个练习",
    "deadline": "2030-01-01T00:00:00Z", "reversible": True, "risk": "low", "context": "30分钟",
    "options": [{"id": "a", "label": "完成练习"}, {"id": "b", "label": "阅读"}], "baseline_option_id": "b"}


def fixture_runner(state, provider, config, evidence=(), **kw):
    return RunResult(recommendation={"option_id": "a", "confidence": .6, "rationale": "测试夹具依据", "source": "fixture",
        "success_probability": None}, provider=provider, model="explicit-test-fixture", evidence_ids=[r["id"] for r in evidence])


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = create_app(self.temp.name, model_runner=fixture_runner)
        self.client = TestClient(self.app, base_url="http://localhost", headers=HEADERS)
        self.addCleanup(self.client.close)

    def post(self, path, data, status=200):
        response = self.client.post("/api/" + path, json=data)
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    def decision(self):
        return self.post("decisions", DECISION, 201)["decision_id"]

    def bootstrap(self):
        response = self.client.get("/api/bootstrap")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_decision_model_human_action_outcome_persist(self):
        d = self.decision()
        state = self.post(f"decisions/{d}/recommend", {"provider": "ollama"})
        self.assertEqual(state["status"], "recommended")
        self.post(f"decisions/{d}/decide", {"option_id": "a"})
        self.assertEqual(len(self.bootstrap()["tasks"]), 1)
        self.assertEqual(len(self.bootstrap()["tasks"]), 1)
        self.post(f"decisions/{d}/resolve", {"success": "yes"})
        restarted = TestClient(create_app(self.temp.name), base_url="http://localhost")
        self.addCleanup(restarted.close)
        data = restarted.get("/api/bootstrap").json()
        self.assertEqual(data["decisions"][0]["status"], "resolved")
        self.assertTrue(data["tasks"][0]["done"])
        self.assertEqual(data["report"]["resolved_decisions"], 1)
        self.assertIsNone(data["decisions"][0]["recommendation"]["success_probability"])

    def test_model_failure_preserves_manual_route(self):
        def fail(*args, **kwargs):
            raise ProviderError("连接失败")
        client = TestClient(create_app(self.temp.name, model_runner=fail), base_url="http://localhost", headers=HEADERS)
        self.addCleanup(client.close)
        d = self.decision()
        self.assertEqual(client.post(f"/api/decisions/{d}/recommend", json={"provider": "ollama"}).status_code, 502)
        self.post(f"decisions/{d}/decide", {"option_id": "b"})
        self.assertEqual(self.bootstrap()["runs"][0]["status"], "failed")

    def test_remote_preview_bound_to_endpoint_and_context(self):
        self.post("settings", {"cloud_url": "https://one.invalid/v1", "cloud_model": "test", "cloud_key": "secret"})
        d = self.decision()
        preview = self.post(f"decisions/{d}/preview", {"provider": "cloud"})
        self.assertTrue(preview["remote"])
        self.assertEqual(preview["endpoint"], "https://one.invalid/v1")
        self.assertEqual(preview["model"], "test")
        self.post("settings", {"cloud_url": "https://two.invalid/v1"})
        self.post(f"decisions/{d}/recommend", {"provider": "cloud", "remote_confirmed": True,
            "snapshot_sha256": preview["snapshot_sha256"]}, 400)
        self.assertEqual(self.bootstrap()["runs"], [])

    def test_local_mutation_boundary(self):
        response = self.client.post("/api/tasks", json={"title": "x"}, headers={"Origin": "https://evil.invalid"})
        self.assertEqual(response.status_code, 403)
        client = TestClient(self.app, base_url="http://localhost")
        self.addCleanup(client.close)
        self.assertEqual(client.post("/api/tasks", json={"title": "x"}).status_code, 403)
        self.assertEqual(self.client.get("/api/health", headers={"Host": "evil.invalid"}).status_code, 400)

    def test_secret_is_never_returned_or_included_in_backup(self):
        settings = self.post("settings", {"cloud_key": "secret-unique"})
        self.assertTrue(settings["cloud_key_set"])
        for path in ("bootstrap", "settings", "backup", "export"):
            self.assertNotIn("secret-unique", self.client.get("/api/" + path).text)
        self.assertEqual((Path(self.temp.name) / "settings.json").stat().st_mode & 0o777, 0o600)
        self.post("settings", {"cloud_key": ""})
        self.assertTrue(self.bootstrap()["settings"]["cloud_key_set"])

    def test_metric_directions_corrections_and_time_window(self):
        for direction, value, expected in (("higher", 8, .8), ("lower", 8, .2), ("target", 5, 1)):
            metric = self.post("metrics", {"name": direction, "minimum": 0, "maximum": 10,
                "direction": direction, "target": 5, "target_count": 7}, 201)
            row = self.post("observations", {"metric_id": metric["id"], "value": 0}, 201)
            self.post("observations", {"metric_id": metric["id"], "value": value, "supersedes": row["id"]}, 201)
            self.post("observations", {"metric_id": metric["id"], "value": 1,
                "observed_at": (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()}, 201)
            score = next(m for m in self.bootstrap()["scores"]["metrics"] if m["id"] == metric["id"])
            self.assertEqual(score["n"], 1)
            self.assertAlmostEqual(score["score"], expected)
            self.assertAlmostEqual(score["coverage"], 1/7)
        self.assertIsNone(self.bootstrap()["scores"]["global_score"])

    def test_documents_retrieved_with_sources_and_redacted_export(self):
        doc = self.post("documents", {"title": "练习记录", "content": "练习是今天可完成的交付", "source": "个人笔记"}, 201)
        d = self.decision()
        preview = self.post(f"decisions/{d}/preview", {"provider": "ollama"})
        self.assertIn(doc["id"], preview["evidence_ids"])
        self.assertFalse(preview["context"]["evidence"][0]["verified"])
        export = self.client.get("/api/export").text
        self.assertNotIn(DECISION["question"], export)
        self.assertNotIn(doc["content"], export)

    def test_backup_restore_and_corruption_rejection(self):
        d = self.decision()
        self.post(f"decisions/{d}/decide", {"option_id": "a"})
        self.post("tasks", {"title": "单独任务"}, 201)
        self.post("reviews", {"text": "下周继续练习", "days": 7}, 201)
        backup = self.client.get("/api/backup").json()
        with tempfile.TemporaryDirectory() as folder:
            other = TestClient(create_app(folder), base_url="http://localhost", headers=HEADERS)
            with other:
                corrupt = copy.deepcopy(backup)
                corrupt["events"][0]["payload"]["question"] = "tampered"
                self.assertEqual(other.post("/api/restore", json=corrupt).status_code, 409)
                self.assertEqual(other.get("/api/bootstrap").json()["tasks"], [])
                self.assertEqual(other.post("/api/restore", json=backup).status_code, 200)
                self.assertEqual(len(other.get("/api/bootstrap").json()["tasks"]), 2)
                self.assertEqual(other.post("/api/restore", json=backup).status_code, 400)
                self.assertFalse((Path(folder) / "restore.pending.json").exists())

    def test_abandon_removes_associated_action(self):
        d = self.decision()
        self.post(f"decisions/{d}/decide", {"option_id": "a"})
        self.post(f"decisions/{d}/abandon", {"reason": "目标已变"})
        self.assertEqual(self.bootstrap()["tasks"], [])
        self.assertEqual(self.bootstrap()["decisions"][0]["status"], "abandoned")

    def test_invalid_input_does_not_create_records(self):
        for body in (DECISION | {"options": 1}, DECISION | {"baseline_option_id": "other"}, DECISION | {"deadline": "bad"}):
            self.post("decisions", body, 400)
        self.post("observations", {"value": 1, "metric_id": "missing"}, 404)
        self.assertEqual(self.bootstrap()["decisions"], [])
        for url in ("http://remote.invalid/v1", "https://:password@remote.invalid/v1", "https://remote.invalid/v1?key=secret"):
            self.post("settings", {"cloud_url": url}, 400)

    def test_interrupted_restore_replays_before_application_serves(self):
        self.decision()
        backup = self.client.get("/api/backup").json()
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "restore.pending.json").write_text(json.dumps(backup))
            with TestClient(create_app(folder), base_url="http://localhost") as other:
                self.assertEqual(len(other.get("/api/bootstrap").json()["decisions"]), 1)
            self.assertFalse(Path(folder, "restore.pending.json").exists())

    def test_incomplete_creation_can_record_baseline_after_restart(self):
        from qone_core.service import DecisionService
        state = DecisionService(self.app.state.ledger).create({k: v for k, v in DECISION.items() if k != "baseline_option_id"})
        result = self.post(f"decisions/{state['decision_id']}/baseline", {"option_id": "a"})
        self.assertEqual(result["status"], "baseline_recorded")
        self.post(f"decisions/{state['decision_id']}/baseline", {"option_id": "b"}, 400)

    def test_backup_invalid_metric_refused_before_any_data_is_written(self):
        self.post("metrics", {"name": "test"}, 201)
        backup = self.client.get("/api/backup").json()
        backup["tables"]["metrics"][0]["maximum"] = 0
        with tempfile.TemporaryDirectory() as folder:
            with TestClient(create_app(folder), base_url="http://localhost", headers=HEADERS) as other:
                self.assertEqual(other.post("/api/restore", json=backup).status_code, 400)
                self.assertEqual(other.get("/api/bootstrap").json()["scores"]["metrics"], [])
