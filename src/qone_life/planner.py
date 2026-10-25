"""Proactive local planner: data-driven refresh, bounded calls, explicit feedback."""
import hashlib
import json
import threading
import time
from datetime import datetime, timezone

from qone_agent.runtime import ProviderError
from .plan_runtime import generate_plan, validate_plan
from .repository import identifier, now


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


CONFIG_FIELDS = ("auto_recommend_provider", "ollama_url", "ollama_model", "laya_checkpoint", "laya_revision", "laya_model_path", "laya_device")


def configuration_digest(config):
    return digest({key: config.get(key) for key in CONFIG_FIELDS})


class Planner:
    def __init__(self, repository, ledger, settings, model_lock, runner=generate_plan):
        self.repo, self.ledger, self.settings, self.model_lock, self.runner = repository, ledger, settings, model_lock, runner
        self.lock, self.wake, self.stopping = threading.RLock(), threading.Event(), threading.Event()
        self.thread = None
        self.current = None
        self.cards = []
        self.input_sha = None
        self.generated_at = None
        self.model_status = "idle"
        self.error = None
        self.last_attempt = 0
        self.attempt_sha = None
        self.attempt_config = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stopping.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True, name="qone-local-recommendations")
        self.thread.start()
        self.notify()

    def stop(self):
        self.stopping.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=1)

    def notify(self):
        self.wake.set()

    def snapshot(self):
        config = self.settings()
        today = datetime.now().astimezone().date().isoformat()
        all_tasks = self.repo.all("tasks")
        reserved = sum(t.get("focus_minutes", t.get("estimate_minutes", 25)) for t in all_tasks if t.get("focus_date") == today)
        config["daily_available_minutes"] = max(0, config["daily_available_minutes"] - reserved)
        goals = [g for g in self.repo.all("goals") if g["status"] == "active"]
        goals.sort(key=lambda g: (-g["priority"], g.get("deadline") or "9999"))
        active_ids = {g["id"] for g in goals}
        goal_map = {g["id"]: g for g in self.repo.all("goals")}
        tasks = [t for t in self.repo.all("tasks") if not t["done"] and
                 (not t.get("goal_id") or t["goal_id"] in active_ids)]
        tasks.sort(key=lambda t: (t.get("deadline") or "9999", -t.get("priority", 3), t["created_at"]))
        candidates = []
        for task in tasks[:6]:
            if task.get("focus_date") == today:
                continue
            linked = goal_map.get(task.get("goal_id"))
            reason = "尚未完成的任务" + (f"；回看期限 {task['deadline']}" if task.get("deadline") else "；尚未设定期限")
            if linked:
                reason += "；关联目标：" + linked["title"]
            candidates.append({"id": "task:" + task["id"], "kind": "task", "task_id": task["id"], "goal_id": task.get("goal_id"),
                "title": task["title"][:200], "reason": reason, "domain": task["domain"],
                "first_step": "对照任务描述，选出这次时间内能完成的一个具体部分；缺少材料时先记录依赖。",
                "done_when": "保存本次产出，并记录任务是否完成；未完成的部分继续保留。",
                "minutes": min(task.get("estimate_minutes", 25), config["daily_available_minutes"]),
                "revision": digest({k: task.get(k) for k in ("title", "deadline", "priority", "goal_id", "done")})})
        linked_tasks = {t.get("goal_id") for t in tasks}
        for goal in goals[:4]:
            if goal["id"] in linked_tasks:
                continue
            completed = [t for t in all_tasks if t.get("goal_id") == goal["id"] and t["done"]]
            title = ("核对下一项缺口：" if completed else "明确第一个交付物：") + goal["title"][:120]
            candidates.append({"id": "goal:" + goal["id"], "kind": "goal", "goal_id": goal["id"], "task_id": None,
                "title": title, "reason": ("已有行动完成，需对照目标核对剩余缺口。" if completed else "该目标还没有未完成的待办，先把下一步的验收范围写清楚。") + "目标优先级 " + str(goal["priority"]) + "/5。",
                "first_step": "对照完成标准，" + ("检查最近产出，写下一个尚未满足的条件。" if completed else "写下一个这次时间内可以交付的小成果，以及如何检查它。"),
                "done_when": "保存一条具体的交付物描述和验收办法；这一步不代表整个目标完成。",
                "domain": goal["domain"], "minutes": min(25, config["daily_available_minutes"]), "revision": digest({"goal": goal, "completed_actions": [{"id": t["id"], "title": t["title"]} for t in all_tasks if t.get("goal_id") == goal["id"] and t["done"]][:8]})})
        for state in self.ledger.project_all().values():
            if state["status"] == "decided" and datetime.fromisoformat(state["deadline"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                candidates.insert(0, {"id": "review:" + state["decision_id"], "kind": "review", "decision_id": state["decision_id"],
                    "task_id": None, "goal_id": None, "title": "回看：" + state["question"][:160],
                    "reason": "已到事前约定的回看时间，结果仍未记录", "domain": state["domain"], "minutes": 5,
                    "first_step": "打开这次选择，对照事前标准填写实际结果。",
                    "done_when": "保存一次结果回看；无法判断时明确记为未知。",
                    "revision": digest({"status": state["status"], "deadline": state["deadline"]})})
        # Preserve feedback without making it part of the model's private context.
        eligible = []
        for candidate in candidates:
            key = "P-" + digest(candidate["id"])[:24]
            candidate["record_id"] = key
            try:
                previous = self.repo.get("suggestions", key)
            except KeyError:
                previous = {}
            if (previous.get("revision") == candidate["revision"] and previous.get("feedback_date") == today
                    and previous.get("status") in {"accepted", "dismissed"}):
                continue
            eligible.append(candidate)
        scores = self.repo.scores(7)
        metrics = [{k: m[k] for k in ("id", "name", "domain", "unit", "direction", "latest_value", "n", "coverage")}
                   for m in scores["metrics"][:6]]
        query = " ".join(g["title"] for g in goals[:3])
        evidence = [e | {"excerpt": e["excerpt"][:600]} for e in self.repo.search(query)[:2]]
        return {"date": today, "available_minutes": config["daily_available_minutes"],
            "goals": [{k: g[k] for k in ("id", "title", "domain", "success_criterion", "priority", "deadline")} for g in goals[:4]],
            "recent_completed_actions": [{"title": t["title"][:200], "goal_id": t.get("goal_id")} for t in all_tasks if t["done"]][:8],
            "recent_observations": metrics, "evidence": evidence, "candidates": eligible[:8] if config["daily_available_minutes"] >= 5 else [],
            "limits": {"goals_included": min(4, len(goals)), "goals_total": len(goals), "pending_tasks_total": len(tasks)}}

    def _prepare(self):
        snapshot = self.snapshot()
        input_sha = digest(snapshot)
        with self.lock:
            if input_sha != self.input_sha:
                self.current, self.input_sha = snapshot, input_sha
                self.generated_at, self.error = now(), None
                self.model_status = "pending" if snapshot["candidates"] else "idle"
                self.cards = []
                budget = snapshot["available_minutes"]
                for candidate in snapshot["candidates"]:
                    if len(self.cards) == 3 or budget < 5:
                        break
                    minutes = min(candidate["minutes"], budget)
                    self.cards.append(self._save(candidate, candidate["title"], candidate["reason"], minutes, "rules", input_sha))
                    budget -= minutes
            if not snapshot["candidates"]:
                self.model_status, self.error = "idle", None
            return snapshot, input_sha

    def _save(self, candidate, title, reason, minutes, source, input_sha, run_id=None, detail=None):
        card = candidate | {"id": candidate["record_id"], "candidate_id": candidate["id"], "title": title, "reason": reason,
            "minutes": minutes, "source": source, "status": "active", "input_sha256": input_sha, "run_id": run_id,
            "created_at": now(), "generated_at": now()}
        card.update({key: (detail or {}).get(key) or candidate.get(key) or "具体内容待细化" for key in ("first_step", "done_when")})
        card["proposal_sha256"] = digest({k: card[k] for k in ("title", "reason", "first_step", "done_when", "minutes", "source", "revision", "input_sha256")})
        self.repo.put("suggestions", card)
        return card

    def state(self):
        snapshot, _ = self._prepare()
        config = self.settings()
        with self.lock:
            return {"enabled": config["auto_recommend_enabled"], "provider": config["auto_recommend_provider"],
                "status": self.model_status if config["auto_recommend_enabled"] else "paused", "error": self.error,
                "date": snapshot["date"], "generated_at": self.generated_at, "input_sha256": self.input_sha,
                "items": self.cards if config["auto_recommend_enabled"] else [],
                "has_goals": bool(snapshot["goals"]), "has_candidates": bool(snapshot["candidates"]),
                "available_minutes": snapshot["available_minutes"], "limits": snapshot["limits"]}

    def tick(self, force=False):
        snapshot, input_sha = self._prepare()
        config = self.settings()
        if not config["auto_recommend_enabled"] or not snapshot["candidates"]:
            return
        # Account for configuration changes but never hash or send cloud credentials.
        config_sha = configuration_digest(config)
        with self.lock:
            retry_after = 300 if self.error else config["auto_recommend_interval_minutes"] * 60
            if (not force and self.attempt_sha == input_sha and self.attempt_config == config_sha
                    and time.monotonic() - self.last_attempt < retry_after):
                return
        if not self.model_lock.acquire(blocking=False):
            return
        started, run_id = now(), identifier("R")
        try:
            with self.lock:
                self.attempt_sha, self.attempt_config, self.last_attempt = input_sha, config_sha, time.monotonic()
                self.model_status = "running"
            result = self.runner(snapshot, config)
            items = validate_plan({"items": result.items}, snapshot)
            run = {"id": run_id, "started_at": started, "status": "completed", "kind": "real_model",
                "purpose": "automatic_recommendation", "provider": result.provider, "model": result.model,
                "duration_ms": result.duration_ms, "usage": result.usage, "input_sha256": input_sha,
                "evidence_snapshot": snapshot["evidence"], "input_snapshot": snapshot, "items": items}
            with self.lock:
                if self.stopping.is_set():
                    return
                if (digest(self.snapshot()) != input_sha or not self.settings()["auto_recommend_enabled"]
                        or configuration_digest(self.settings()) != config_sha):
                    run["status"] = "discarded"
                    self.repo.put("runs", run)
                    self.model_status = "pending"
                    self.notify()
                    return
                candidates = {c["id"]: c for c in snapshot["candidates"]}
                self.cards = [self._save(candidates[item["candidate_id"]], item["title"], item["reason"], item["minutes"],
                                         result.provider + ":" + result.model, input_sha, run_id, item) for item in items]
                self.repo.put("runs", run)
                self.generated_at, self.model_status, self.error = now(), "ready", None
        except ProviderError as exc:
            with self.lock:
                if not self.stopping.is_set():
                    self.model_status, self.error = "rules", str(exc)
                    self.repo.put("runs", {"id": run_id, "started_at": started, "status": "failed", "kind": "real_model",
                        "purpose": "automatic_recommendation", "provider": config["auto_recommend_provider"], "error": str(exc), "input_sha256": input_sha})
        finally:
            self.model_lock.release()

    def feedback(self, record_id, action, proposal_sha=None):
        if action not in {"accept", "dismiss"}:
            raise ValueError("请选择采纳或今天忽略")
        with self.lock:
            self._prepare()
            matches = [c for c in self.cards if c["id"] == record_id]
            if not matches:
                raise ValueError("这条推荐已变化，请查看最新推荐")
            card = matches[0]
            if proposal_sha is not None and proposal_sha != card["proposal_sha256"]:
                raise ValueError("这条推荐的内容已更新，请审阅后再采纳")
            if action == "accept" and card["kind"] != "review":
                task_id = card.get("task_id") or "goal-action-" + digest({"goal": card["goal_id"], "stage": card["revision"], "date": self.current["date"]})[:24]
                try:
                    task = self.repo.get("tasks", task_id)
                except KeyError:
                    task = {"id": task_id, "title": card["title"], "domain": card["domain"], "done": False,
                        "deadline": None, "created_at": now(), "decision_id": None, "goal_id": card.get("goal_id"),
                        "estimate_minutes": card["minutes"], "priority": 3}
                self.repo.put("tasks", task | {"focus_date": self.current["date"], "focus_minutes": card["minutes"], "focus_recommendation": card})
            self.repo.put("suggestions", card | {"status": "accepted" if action == "accept" else "dismissed",
                "feedback_date": self.current["date"]})
            self.notify()
            return {"ok": True, "decision_id": card.get("decision_id") if action == "accept" else None}

    def _loop(self):
        while not self.stopping.is_set():
            self.wake.wait(30)
            self.wake.clear()
            if self.stopping.is_set():
                break
            try:
                self.tick()
            except Exception:
                # A corrupt local record must not kill the scheduler or expose private text.
                with self.lock:
                    self.model_status, self.error = "error", "自动推荐暂时无法更新，请检查本地数据与模型连接"
                self.stopping.wait(5)
