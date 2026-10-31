"""主动式本地规划器：数据驱动的刷新、有界调用与显式反馈。"""
import hashlib
import json
import threading
import time
from datetime import datetime, timezone

from qone_agent.runtime import ProviderError

from .plan_runtime import generate_plan, validate_plan
from .repository import identifier, now
from .system import SystemService


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


CONFIG_FIELDS = ("auto_recommend_provider", "ollama_url", "ollama_model", "laya_checkpoint", "laya_revision", "laya_model_path", "laya_device")


def configuration_digest(config):
    return digest({key: config.get(key) for key in CONFIG_FIELDS})


class Planner:
    def __init__(self, repository, ledger, settings, model_lock, runner=generate_plan):
        self.repo = repository
        self.ledger = ledger
        self.settings = settings
        self.model_lock = model_lock
        self.runner = runner
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.stopping = threading.Event()
        self.thread = None
        self.current = None
        self.cards = []
        self.input_sha = None
        self.generated_at = None
        self.model_status = "idle"
        self.error = None
        self.system = SystemService(repository, self.lock)
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
        """收集当前所有可用于生成推荐的本地事实，构造本次快照。"""
        config = self.settings()
        english = str(config.get("resolved_language", "zh-CN")).lower().startswith("en")
        today = datetime.now().astimezone().date().isoformat()
        all_tasks = self.repo.all("tasks")

        # 今日已被其它推荐占用的时间要从每日可用额度中扣除。
        reserved = 0
        for t in all_tasks:
            if t.get("focus_date") == today:
                reserved += t.get("focus_minutes", t.get("estimate_minutes", 25))
        config["daily_available_minutes"] = max(0, config["daily_available_minutes"] - reserved)

        advanced = self.system.planning_snapshot(today=today, available_minutes=config["daily_available_minutes"])
        if advanced is not None:
            return advanced

        goals = [g for g in self.repo.all("goals") if g["status"] == "active"]
        goals.sort(key=lambda g: (-g["priority"], g.get("deadline") or "9999"))
        active_ids = {g["id"] for g in goals}
        goal_map = {g["id"]: g for g in self.repo.all("goals")}

        # 只保留未完成、且未关联到已失活目标的任务。
        tasks = []
        for t in self.repo.all("tasks"):
            if t["done"]:
                continue
            if t.get("goal_id") and t["goal_id"] not in active_ids:
                continue
            tasks.append(t)
        tasks.sort(key=lambda t: (t.get("deadline") or "9999", -t.get("priority", 3), t["created_at"]))

        candidates = []
        for task in tasks[:6]:
            if task.get("focus_date") == today:
                continue
            linked = goal_map.get(task.get("goal_id"))

            if english:
                if task.get("deadline"):
                    reason = "An unfinished task" + f"; review by {task['deadline']}"
                else:
                    reason = "An unfinished task" + "; no deadline set"
            else:
                if task.get("deadline"):
                    reason = "尚未完成的任务" + f"；回看期限 {task['deadline']}"
                else:
                    reason = "尚未完成的任务" + "；尚未设定期限"
            if linked:
                if english:
                    reason += "; linked goal: " + linked["title"]
                else:
                    reason += "；关联目标：" + linked["title"]

            if english:
                first_step = "Choose one concrete part of this task that fits the available time; record any missing dependency first."
                done_when = "Save the output and record whether the task is complete; keep unfinished parts on the list."
            else:
                first_step = "对照任务描述，选出这次时间内能完成的一个具体部分；缺少材料时先记录依赖。"
                done_when = "保存本次产出，并记录任务是否完成；未完成的部分继续保留。"

            revision = digest({k: task.get(k) for k in ("title", "deadline", "priority", "goal_id", "done")})
            candidates.append({"id": "task:" + task["id"], "kind": "task", "task_id": task["id"], "goal_id": task.get("goal_id"),
                "title": task["title"][:200], "reason": reason, "domain": task["domain"],
                "first_step": first_step,
                "done_when": done_when,
                "minutes": task.get("estimate_minutes", 25),
                "revision": revision})

        linked_tasks = {t.get("goal_id") for t in tasks}
        for goal in goals[:4]:
            if goal["id"] in linked_tasks:
                continue
            completed = [t for t in all_tasks if t.get("goal_id") == goal["id"] and t["done"]]

            if english:
                if completed:
                    title = "Check the next gap: " + goal["title"][:120]
                    reason = "Completed actions exist; compare the current output with the remaining success criteria."
                else:
                    title = "Define the first deliverable: " + goal["title"][:120]
                    reason = "This goal has no open action yet; define the next verifiable slice first."
                reason = reason + f" Goal priority {goal['priority']}/5."
                if completed:
                    first_step = "Compare the latest output with the success criterion and write one condition that is still unmet."
                else:
                    first_step = "Write one small deliverable for this session and how you will check it."
                done_when = "Save a concrete deliverable description and its acceptance check; this does not complete the whole goal."
            else:
                if completed:
                    title = "核对下一项缺口：" + goal["title"][:120]
                    reason = "已有行动完成，需对照目标核对剩余缺口。"
                else:
                    title = "明确第一个交付物：" + goal["title"][:120]
                    reason = "该目标还没有未完成的待办，先把下一步的验收范围写清楚。"
                reason = reason + "目标优先级 " + str(goal["priority"]) + "/5。"
                if completed:
                    first_step = "对照完成标准，" + "检查最近产出，写下一个尚未满足的条件。"
                else:
                    first_step = "对照完成标准，" + "写下一个这次时间内可以交付的小成果，以及如何检查它。"
                done_when = "保存一条具体的交付物描述和验收办法；这一步不代表整个目标完成。"

            completed_actions = []
            for t in all_tasks:
                if t.get("goal_id") == goal["id"] and t["done"]:
                    completed_actions.append({"id": t["id"], "title": t["title"]})
            completed_actions = completed_actions[:8]
            candidates.append({"id": "goal:" + goal["id"], "kind": "goal", "goal_id": goal["id"], "task_id": None,
                "title": title, "reason": reason,
                "first_step": first_step,
                "done_when": done_when,
                "domain": goal["domain"], "minutes": min(25, config["daily_available_minutes"]),
                "revision": digest({"goal": goal, "completed_actions": completed_actions})})

        # 已到期、但结果仍未记录的决定，插到最前面提醒回看。
        for state in self.ledger.project_all().values():
            if state["status"] == "decided" and datetime.fromisoformat(state["deadline"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                if english:
                    title = "Review: " + state["question"][:160]
                    reason = "The review time set before acting has arrived, but the outcome is still unrecorded."
                    first_step = "Open this decision and record the actual result against the criterion set in advance."
                    done_when = "Save one outcome review; record it explicitly as unknown when it cannot be judged."
                else:
                    title = "回看：" + state["question"][:160]
                    reason = "已到事前约定的回看时间，结果仍未记录"
                    first_step = "打开这次选择，对照事前标准填写实际结果。"
                    done_when = "保存一次结果回看；无法判断时明确记为未知。"
                candidates.insert(0, {"id": "review:" + state["decision_id"], "kind": "review", "decision_id": state["decision_id"],
                    "task_id": None, "goal_id": None,
                    "title": title,
                    "reason": reason,
                    "domain": state["domain"], "minutes": 5,
                    "first_step": first_step,
                    "done_when": done_when,
                    "revision": digest({"status": state["status"], "deadline": state["deadline"]})})

        # 保留用户反馈，但不把它放进模型可见的私有上下文。
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
        metrics = []
        for m in scores["metrics"][:6]:
            metrics.append({k: m[k] for k in ("id", "name", "domain", "unit", "direction", "latest_value", "n", "coverage")})

        goal_titles = []
        for g in goals[:3]:
            goal_titles.append(g["title"])
        query = " ".join(goal_titles)
        evidence = []
        for e in self.repo.search(query)[:2]:
            evidence.append(e | {"excerpt": e["excerpt"][:600]})

        goal_views = []
        for g in goals[:4]:
            goal_views.append({k: g[k] for k in ("id", "title", "domain", "success_criterion", "priority", "deadline")})

        recent_completed = []
        for t in all_tasks:
            if t["done"]:
                recent_completed.append({"title": t["title"][:200], "goal_id": t.get("goal_id")})
        recent_completed = recent_completed[:8]

        # 每日可用时间不足 5 分钟时不再给出候选。
        if config["daily_available_minutes"] >= 5:
            limited_candidates = []
            for c in eligible:
                if c["minutes"] <= config["daily_available_minutes"]:
                    limited_candidates.append(c)
            limited_candidates = limited_candidates[:8]
        else:
            limited_candidates = []

        return {"date": today, "available_minutes": config["daily_available_minutes"],
            "goals": goal_views,
            "recent_completed_actions": recent_completed,
            "recent_observations": metrics, "evidence": evidence, "candidates": limited_candidates,
            "limits": {"goals_included": min(4, len(goals)), "goals_total": len(goals), "pending_tasks_total": len(tasks)}}

    def _prepare(self):
        with self.lock:
            snapshot = self.snapshot()
            input_sha = digest(snapshot)
            if input_sha != self.input_sha:
                self.current, self.input_sha = snapshot, input_sha
                self.generated_at, self.error = now(), None
                if snapshot["candidates"]:
                    self.model_status = "pending"
                else:
                    self.model_status = "idle"
                self.cards = []
                budget = snapshot["available_minutes"]
                for candidate in snapshot["candidates"]:
                    if len(self.cards) == 3 or budget < 5:
                        break
                    if candidate["minutes"] > budget:
                        continue
                    minutes = candidate["minutes"]
                    # 根据系统模式决定来源标记。
                    if snapshot.get("system"):
                        if snapshot.get("system", {}).get("mode") == "adaptive":
                            source = "adaptive"
                        else:
                            source = "scenario"
                    else:
                        source = "rules"
                    self.cards.append(self._save(candidate, candidate["title"], candidate["reason"], minutes, source, input_sha))
                    budget -= minutes
            if snapshot.get("system"):
                if self.cards:
                    self.model_status = "conditional"
                else:
                    self.model_status = "needs_information"
            elif not snapshot["candidates"]:
                self.model_status = "idle"
                self.error = None
            return snapshot, input_sha

    def _save(self, candidate, title, reason, minutes, source, input_sha, run_id=None, detail=None):
        card = candidate | {"id": candidate["record_id"], "candidate_id": candidate["id"], "title": title, "reason": reason,
            "minutes": minutes, "source": source, "status": "active", "input_sha256": input_sha, "run_id": run_id,
            "created_at": now(), "generated_at": now()}
        english = str(self.settings().get("resolved_language", "zh-CN")).lower().startswith("en")
        fallback = "具体内容待细化"
        if english:
            fallback = "Details need refinement"
        refined = {}
        for key in ("first_step", "done_when"):
            value = (detail or {}).get(key)
            if not value:
                value = candidate.get(key)
            if not value:
                value = fallback
            refined[key] = value
        card.update(refined)
        card["proposal_sha256"] = digest({k: card[k] for k in ("title", "reason", "first_step", "done_when", "minutes", "source", "revision", "input_sha256")})
        self.repo.put("suggestions", card)
        return card

    def state(self):
        snapshot, _ = self._prepare()
        config = self.settings()
        with self.lock:
            if config["auto_recommend_enabled"]:
                status = self.model_status
                items = self.cards
            else:
                status = "paused"
                items = []
            return {"enabled": config["auto_recommend_enabled"], "provider": config["auto_recommend_provider"],
                "status": status, "error": self.error,
                "date": snapshot["date"], "generated_at": self.generated_at, "input_sha256": self.input_sha,
                "items": items,
                "has_goals": bool(snapshot["goals"]), "has_candidates": bool(snapshot["candidates"]),
                "available_minutes": snapshot["available_minutes"], "limits": snapshot["limits"], "system": snapshot.get("system")}

    def tick(self, force=False):
        snapshot, input_sha = self._prepare()
        config = self.settings()
        if snapshot.get("system") or not config["auto_recommend_enabled"] or not snapshot["candidates"]:
            return
        # 记录配置变化，但绝不对云端凭证做哈希或外发。
        config_sha = configuration_digest(config)
        retry_after = config["auto_recommend_interval_minutes"] * 60
        if self.error:
            retry_after = 300
        with self.lock:
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
                cards = []
                for item in items:
                    candidate = candidates[item["candidate_id"]]
                    cards.append(self._save(candidate, item["title"], item["reason"], item["minutes"],
                                            result.provider + ":" + result.model, input_sha, run_id, item))
                self.cards = cards
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
                task_id = card.get("task_id") or "goal-action-" + digest({"goal": card["goal_id"], "stage": card["revision"], "system_action":card.get("system_action_id"), "date": self.current["date"]})[:24]
                try:
                    task = self.repo.get("tasks", task_id)
                except KeyError:
                    task = {"id": task_id, "title": card["title"], "domain": card["domain"], "done": False,
                        "deadline": None, "created_at": now(), "decision_id": None, "goal_id": card.get("goal_id"),
                        "estimate_minutes": card["minutes"], "priority": 3}
                if card["kind"] == "system":
                    task.update({k:card[k] for k in ("system_action_id","system_action_sha256","system_commitments","system_revision")})
                    # 找出与该系统候选对应的情景预测。
                    system_prediction = None
                    for s in self.current["system"]["comparison"]["scenarios"]:
                        if s["id"] == card["system_scenario"]:
                            system_prediction = s
                            break
                    if system_prediction is None:
                        raise StopIteration
                    task["system_prediction"] = system_prediction
                self.repo.put("tasks", task | {"focus_date": self.current["date"], "focus_minutes": card["minutes"], "focus_recommendation": card})
            feedback_status = "dismissed"
            if action == "accept":
                feedback_status = "accepted"
            self.repo.put("suggestions", card | {"status": feedback_status,
                "feedback_date": self.current["date"]})
            self.notify()
            decision_id = None
            if action == "accept":
                decision_id = card.get("decision_id")
            return {"ok": True, "decision_id": decision_id}

    def _loop(self):
        while not self.stopping.is_set():
            self.wake.wait(30)
            self.wake.clear()
            if self.stopping.is_set():
                break
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - 调度器兜底：单条损坏记录不能杀死循环
                # 单条本地损坏记录不能杀死调度器，也不能暴露私有文本。
                with self.lock:
                    self.model_status, self.error = "error", "自动推荐暂时无法更新，请检查本地数据与模型连接"
                self.stopping.wait(5)
