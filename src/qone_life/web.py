"""Q-One: a local, single-user Chinese workspace backed by real model adapters."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import secrets
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from qone_agent.runtime import ProviderError, is_loopback, public_context, run_model
from qone_core.ledger import Ledger, LedgerError
from qone_core.report import build_report
from qone_core.service import DecisionService
from .planner import Planner
from .plan_runtime import generate_plan
from .backup import TABLES, apply_pending, validate_backup
from .repository import DOMAINS, Repository, identifier, now, timestamp

STATIC = Path(__file__).parent / "static"
DEFAULTS = {
    "auto_recommend_enabled": True, "auto_recommend_provider": "ollama",
    "auto_recommend_interval_minutes": 360, "daily_available_minutes": 90,
    "ollama_url": "http://127.0.0.1:11434", "ollama_model": "qwen3:8b",
    "cloud_url": "", "cloud_model": "", "cloud_key": "",
    "laya_checkpoint": "convaiinnovations/laya-multilingual",
    "laya_revision": "1720e3e3357cfe1e281542e223f8273b0890ca34",
    "laya_model_path": "", "laya_device": "cpu", "default_provider": "ollama",
}


def create_app(data_dir=None, *, model_runner=run_model, plan_runner=generate_plan):
    directory = Path(data_dir or os.environ.get("QONE_HOME", Path.home() / ".local/share/q-one"))
    repository = Repository(directory)
    ledger = Ledger(directory / "decisions.jsonl")
    apply_pending(directory, repository, ledger)
    decisions = DecisionService(ledger)
    lock = threading.RLock()
    model_lock = threading.Lock()
    settings_path = directory / "settings.json"
    @asynccontextmanager
    async def lifespan(app):
        app.state.planner.start()
        try:
            yield
        finally:
            app.state.planner.stop()

    app = FastAPI(lifespan=lifespan, title="Q-One 人生系统", version="0.5.0", docs_url="/api/docs", redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])
    app.state.repository, app.state.ledger = repository, ledger

    def settings():
        saved = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        return DEFAULTS | saved | ({"cloud_key": os.environ["QONE_CLOUD_API_KEY"]} if os.environ.get("QONE_CLOUD_API_KEY") else {})

    def public_settings():
        value = settings()
        value["cloud_key_set"] = bool(value.pop("cloud_key", ""))
        value["laya_installed"] = importlib.util.find_spec("laya") is not None
        return value

    def save_settings(raw):
        current = settings()
        for key in DEFAULTS:
            if key in raw:
                if key == "auto_recommend_enabled":
                    if type(raw[key]) is not bool:
                        raise ValueError("自动推荐开关必须为开或关")
                    current[key] = raw[key]
                    continue
                if key in {"auto_recommend_interval_minutes", "daily_available_minutes"}:
                    bounds = (15, 1440) if key == "auto_recommend_interval_minutes" else (5, 480)
                    if type(raw[key]) is not int or not bounds[0] <= raw[key] <= bounds[1]:
                        raise ValueError("自动推荐间隔或每日时间超出允许范围")
                    current[key] = raw[key]
                    continue
                if not isinstance(raw[key], str):
                    raise ValueError("设置项必须为文本")
                if key == "cloud_key" and raw[key] == "":
                    continue  # Empty input preserves the existing secret.
                current[key] = raw[key].strip()
        if raw.get("clear_cloud_key"):
            current["cloud_key"] = ""
        for key in ("ollama_url", "cloud_url"):
            if current[key]:
                parsed = urlparse(current[key])
                if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None or parsed.query or parsed.fragment:
                    raise ValueError("模型基础地址需为有效HTTP地址，不能包含密码、查询参数或片段")
                if not is_loopback(current[key]) and parsed.scheme != "https":
                    raise ValueError("远程模型地址必须使用HTTPS")
        if current["auto_recommend_provider"] not in {"ollama", "laya"}:
            raise ValueError("自动推荐请选择本地Ollama或Laya")
        if current["default_provider"] not in {"ollama", "laya", "cloud"}:
            raise ValueError("默认模型无效")
        if current["laya_device"] not in {"cpu", "cuda"}:
            raise ValueError("Laya设备仅支持cpu或cuda")
        with lock:
            fd, temporary = tempfile.mkstemp(prefix="settings-", dir=directory)
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "w") as handle:
                    json.dump(current, handle, ensure_ascii=False, allow_nan=False)
                os.replace(temporary, settings_path)
            finally:
                Path(temporary).unlink(missing_ok=True)
        return public_settings()

    planner = Planner(repository, ledger, settings, model_lock, runner=plan_runner)
    app.state.planner = planner

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and urlparse(origin).netloc != request.headers.get("host"):
                return JSONResponse({"detail": "只接受当前页面发出的操作"}, status_code=403)
            if request.headers.get("x-qone-client") != "web":
                return JSONResponse({"detail": "缺少本地客户端标识"}, status_code=403)
            if request.method != "DELETE" and "application/json" not in request.headers.get("content-type", ""):
                return JSONResponse({"detail": "请求需为JSON格式"}, status_code=415)
            body = await request.body()
            if len(body) > 4 * 1024 * 1024:
                return JSONResponse({"detail": "单次数据不能超过4MB"}, status_code=413)
        response = await call_next(request)
        if request.method in {"POST", "PATCH", "PUT", "DELETE"} and response.status_code < 400:
            planner.notify()
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ValueError)
    async def bad_value(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(TypeError)
    async def bad_type(request, exc):
        return JSONResponse({"detail": "字段类型无效，请检查数值与文本"}, status_code=400)

    @app.exception_handler(KeyError)
    async def not_found(request, exc):
        return JSONResponse({"detail": "记录不存在"}, status_code=404)

    @app.exception_handler(LedgerError)
    async def corrupt_ledger(request, exc):
        return JSONResponse({"detail": "决策记录完整性校验失败，请从本地备份检查恢复"}, status_code=409)

    @app.exception_handler(RequestValidationError)
    async def malformed(request, exc):
        return JSONResponse({"detail": "提交的数据格式不正确，请检查必填字段"}, status_code=422)

    def public_decisions():
        return [{k: v for k, v in state.items() if k != "events"}
                for state in reversed(list(ledger.project_all().values()))]

    def sync_tasks():
        for state in ledger.project_all().values():
            if state["status"] not in {"decided", "resolved"}:
                continue
            task_id = "decision-" + state["decision_id"]
            try:
                repository.get("tasks", task_id)
                continue
            except KeyError:
                pass
            option = next(o for o in state["options"] if o["id"] == state["human_decision"]["option_id"])
            repository.put("tasks", {"id": task_id, "title": option["label"], "domain": state["domain"],
                "deadline": state["deadline"], "done": state["status"] == "resolved" and state["outcome"]["success"] == "yes",
                "decision_id": state["decision_id"], "created_at": now()})

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.5.0", "ledger_events": ledger.verify(), "storage": "local"}

    @app.get("/api/bootstrap")
    def bootstrap(days: int = 7):
        if days not in {7, 30, 90}:
            raise ValueError("请选择7、30或90天窗口")
        with lock:
            sync_tasks()
            return {"goals": repository.all("goals"), "planner": planner.state(), "decisions": public_decisions(), "tasks": repository.all("tasks"),
                "scores": repository.scores(days), "report": build_report(ledger), "domains": DOMAINS,
                "documents": [{k: v for k, v in row.items() if k != "content"} for row in repository.all("documents")],
                "reviews": repository.all("reviews"), "runs": repository.all("runs")[:30],
                "settings": public_settings(), "demo": bool(os.environ.get("QONE_DEMO"))}

    @app.post("/api/decisions", status_code=201)
    def create_decision(raw: dict):
        if not isinstance(raw.get("options"), list):
            raise ValueError("请填写2到8个备选方案")
        baseline = raw.get("baseline_option_id")
        if baseline not in {o.get("id") for o in raw.get("options", []) if isinstance(o, dict)}:
            raise ValueError("请先选出你自己的初始选择")
        if raw.get("domain") not in DOMAINS:
            raise ValueError("领域无效")
        raw = {k: v for k, v in raw.items() if k != "baseline_option_id"}
        if len(str(raw.get("question", ""))) > 500 or len(str(raw.get("context", ""))) > 15000:
            raise ValueError("问题最多500字，背景最多15000字")
        with lock:
            state = decisions.create(raw)
            decisions.baseline(state["decision_id"], baseline)
            return ledger.get(state["decision_id"])

    @app.get("/api/decisions/{decision_id}")
    def get_decision(decision_id: str):
        return ledger.get(decision_id)

    def preview_digest(context, provider, config):
        binding = {"context": context, "provider": provider, "url": config.get("cloud_url") if provider == "cloud" else config.get("ollama_url"),
            "model": config.get("cloud_model") if provider == "cloud" else config.get("ollama_model"),
            "revision": config.get("laya_revision")}
        return hashlib.sha256(json.dumps(binding, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    @app.post("/api/decisions/{decision_id}/preview")
    def preview(decision_id: str, raw: dict):
        state = ledger.get(decision_id)
        evidence = repository.search(state["question"] + " " + state["success_criterion"]) if raw.get("use_evidence", True) else []
        context = public_context(state, evidence)
        config = settings()
        provider = raw.get("provider", config["default_provider"])
        url = config.get("cloud_url", "") if provider == "cloud" else config["ollama_url"]
        return {"context": context, "remote": provider != "laya" and not is_loopback(url),
                "evidence_ids": [row["id"] for row in evidence], "provider": provider,
                "endpoint": "本机Laya进程" if provider == "laya" else url,
                "model": config["laya_checkpoint"] if provider == "laya" else config["cloud_model"] if provider == "cloud" else config["ollama_model"],
                "snapshot_sha256": preview_digest(context, provider, config)}

    @app.post("/api/decisions/{decision_id}/recommend")
    def recommend(decision_id: str, raw: dict):
        state = ledger.get(decision_id)
        if state["status"] != "baseline_recorded":
            raise ValueError("只能在记录初始选择后、最终决定前获取一次建议")
        config = settings()
        provider = raw.get("provider", config["default_provider"])
        evidence = repository.search(state["question"] + " " + state["success_criterion"]) if raw.get("use_evidence", True) else []
        prepared = public_context(state, evidence)
        digest = preview_digest(prepared, provider, config)
        endpoint = config.get("cloud_url", "") if provider == "cloud" else config["ollama_url"]
        remote = provider != "laya" and not is_loopback(endpoint)
        if remote and (raw.get("remote_confirmed") is not True or raw.get("snapshot_sha256") != digest):
            raise ValueError("请先预览当前发送内容并确认；内容变化后需要重新预览")
        if not model_lock.acquire(blocking=False):
            raise HTTPException(409, "已有模型任务正在运行，请稍后重试")
        run_id = identifier("R")
        started = now()
        try:
            result = model_runner(state, provider, config, evidence,
                                  remote_confirmed=bool(raw.get("remote_confirmed")))
            with lock:
                decisions.recommend(decision_id, result.recommendation, run_id=result.run_id,
                                    evidence_ids=result.evidence_ids)
                repository.put("runs", result.receipt() | {"id": result.run_id, "decision_id": decision_id,
                    "started_at": started, "status": "completed", "kind": "real_model",
                    "evidence_snapshot": evidence})
            return ledger.get(decision_id)
        except ProviderError as exc:
            repository.put("runs", {"id": run_id, "decision_id": decision_id, "provider": provider,
                "started_at": started, "status": "failed", "kind": "real_model", "error": str(exc)})
            raise HTTPException(502, str(exc)) from exc
        finally:
            model_lock.release()

    @app.post("/api/decisions/{decision_id}/baseline")
    def record_baseline(decision_id: str, raw: dict):
        decisions.baseline(decision_id, raw.get("option_id"))
        return ledger.get(decision_id)

    @app.post("/api/decisions/{decision_id}/decide")
    def decide(decision_id: str, raw: dict):
        with lock:
            decisions.decide(decision_id, raw.get("option_id"), raw.get("reason", ""))
            sync_tasks()
            return ledger.get(decision_id)

    @app.post("/api/decisions/{decision_id}/resolve")
    def resolve(decision_id: str, raw: dict):
        with lock:
            decisions.resolve(decision_id, raw.get("success"), raw.get("notes", ""))
            task_id = "decision-" + decision_id
            sync_tasks()
            task = repository.get("tasks", task_id)
            repository.put("tasks", task | {"done": raw.get("success") == "yes"})
            return ledger.get(decision_id)

    @app.post("/api/decisions/{decision_id}/abandon")
    def abandon(decision_id: str, raw: dict):
        with lock:
            decisions.abandon(decision_id, raw.get("reason", ""))
            repository.remove("tasks", "decision-" + decision_id)
            return ledger.get(decision_id)

    @app.get("/api/system")
    def get_system():
        return {"current":planner.system.current()}

    @app.post("/api/system", status_code=201)
    def save_system(raw: dict):
        if "parent_revision" not in raw or not isinstance(raw.get("model"),dict):
            raise ValueError("需要model和parent_revision；首次导入的parent_revision为null")
        with planner.lock:
            result=planner.system.save(raw["model"],raw["parent_revision"])
            planner.input_sha=None
            return result

    @app.post("/api/system/evaluate")
    def evaluate_system(raw: dict):
        with planner.lock:
            result=planner.system.evaluate(raw.get("as_of",now()),available_minutes=raw.get("available_minutes",settings()["daily_available_minutes"]),
                max_actions=raw.get("max_actions",3),horizon_days=raw.get("horizon_days"))
            if result is None: raise ValueError("请先导入并声明人生模型")
            return result

    @app.post("/api/system/replay")
    def replay_system(raw: dict):
        with planner.lock:
            _,kernel=planner.system.kernel()
            if kernel is None or not hasattr(kernel,"replay"): raise ValueError("当前模型尚未配置历史学习记录")
            return kernel.replay()

    @app.get("/api/planner")
    def recommendation_feed():
        return planner.state()

    @app.post("/api/planner/refresh", status_code=202)
    def refresh_recommendations(raw: dict):
        with planner.lock:
            planner.attempt_sha = None
        planner.notify()
        return {"queued": True}

    @app.post("/api/planner/{record_id}/feedback")
    def recommendation_feedback(record_id: str, raw: dict):
        with lock:
            if not isinstance(raw.get("proposal_sha256"), str):
                raise ValueError("请使用当前页面中的推荐")
            return planner.feedback(record_id, raw.get("action"), raw["proposal_sha256"])

    @app.post("/api/goals", status_code=201)
    def create_goal(raw: dict):
        return repository.goal(raw)

    @app.patch("/api/goals/{goal_id}")
    def update_goal(goal_id: str, raw: dict):
        with lock:
            return repository.goal(raw, goal_id)

    @app.post("/api/tasks", status_code=201)
    def create_task(raw: dict):
        title = str(raw.get("title", "")).strip()
        domain = raw.get("domain", "work")
        if not title or len(title) > 300 or domain not in DOMAINS:
            raise ValueError("请填写有效的任务与领域")
        goal_id = raw.get("goal_id") or None
        if goal_id:
            repository.get("goals", goal_id)
        minutes, priority = raw.get("estimate_minutes", 25), raw.get("priority", 3)
        if type(minutes) is not int or not 5 <= minutes <= 480 or type(priority) is not int or not 1 <= priority <= 5:
            raise ValueError("任务时长或优先级无效")
        return repository.put("tasks", {"goal_id": goal_id, "estimate_minutes": minutes, "priority": priority, "id": identifier("T"), "title": title, "domain": domain,
            "deadline": timestamp(raw["deadline"]) if raw.get("deadline") else None,
            "done": False, "created_at": now(), "decision_id": None})

    @app.patch("/api/tasks/{task_id}")
    def update_task(task_id: str, raw: dict):
        with lock:
            task = repository.get("tasks", task_id)
            if type(raw.get("done")) is not bool:
                raise ValueError("任务状态应为完成或未完成")
            return repository.put("tasks", task | {"done": raw["done"], "completed_at": now() if raw["done"] else None})

    @app.delete("/api/tasks/{task_id}")
    def delete_task(task_id: str):
        task = repository.get("tasks", task_id)
        if task.get("decision_id"):
            raise ValueError("决策任务请在决策页结算，以保留结果")
        repository.remove("tasks", task_id)
        return {"ok": True}

    @app.post("/api/metrics", status_code=201)
    def create_metric(raw: dict):
        return repository.metric(raw)

    @app.post("/api/observations", status_code=201)
    def add_observation(raw: dict):
        with lock:
            return repository.observation(raw)

    @app.post("/api/documents", status_code=201)
    def add_document(raw: dict):
        return repository.document(raw)

    @app.get("/api/documents/{document_id}")
    def get_document(document_id: str):
        return repository.get("documents", document_id)

    @app.delete("/api/documents/{document_id}")
    def delete_document(document_id: str):
        repository.remove("documents", document_id)
        return {"ok": True}

    @app.get("/api/search")
    def search(q: str = ""):
        return {"items": repository.search(q, 10)}

    @app.post("/api/reviews", status_code=201)
    def save_review(raw: dict):
        text = str(raw.get("text", "")).strip()
        days = raw.get("days", 7)
        if not text or len(text) > 12000 or days not in {7, 30, 90}:
            raise ValueError("请填写复盘内容，并选择有效窗口")
        return repository.put("reviews", {"id": identifier("V"), "created_at": now(), "days": days,
            "text": text, "snapshot": {"scores": repository.scores(days), "decisions": len(public_decisions()),
                                        "report": build_report(ledger)}})

    @app.get("/api/settings")
    def read_settings():
        return public_settings()

    @app.post("/api/settings")
    def update_settings(raw: dict):
        return save_settings(raw)

    @app.get("/api/providers")
    def providers():
        config = settings()
        ollama = {"available": False, "models": [], "error": None}
        if is_loopback(config["ollama_url"]):
            try:
                with httpx.Client(timeout=3, trust_env=False) as client:
                    response = client.get(config["ollama_url"].rstrip("/") + "/api/tags")
                    response.raise_for_status()
                    ollama.update(available=True, models=[m["name"] for m in response.json().get("models", [])])
            except (httpx.HTTPError, ValueError, KeyError):
                ollama["error"] = "本地Ollama尚未连接"
        return {"ollama": ollama, "laya": {"installed": importlib.util.find_spec("laya") is not None,
                "checkpoint": config["laya_checkpoint"]}, "cloud": {"configured": bool(config["cloud_url"] and config["cloud_model"])}}

    @app.get("/api/export")
    def export():
        # Redacted summary excludes all free text, exact times, IDs and raw option labels.
        states = public_decisions()
        result = {"format": "q-one-redacted-summary-v1", "created_date": now()[:10],
            "decisions": [{"id": secrets.token_hex(8), "domain": s["domain"], "status": s["status"],
                "success": s.get("outcome", {}).get("success")} for s in states],
            "metrics": [{"id": secrets.token_hex(8), "domain": m["domain"], "n": m["n"],
                "score": m["score"]} for m in repository.scores(7)["metrics"]],
            "notice": "已移除自由文本、精确时间和关联ID；摘要仍可能敏感，请检查后再分享"}
        return JSONResponse(result, headers={"Content-Disposition": 'attachment; filename="q-one-summary.json"'})

    @app.get("/api/backup")
    def backup():
        with lock, planner.lock:
            result = {"format": "q-one-backup-v3", "created_at": now(), "events": ledger.events(),
                "tables": {name: repository.all(name) for name in TABLES}}
        return JSONResponse(result, headers={"Content-Disposition": 'attachment; filename="q-one-private-backup.json"'})

    @app.post("/api/restore")
    def restore(raw: dict):
        try:
            validate_backup(raw)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("备份字段不完整或类型无效") from exc
        with lock, planner.lock:
            if ledger.events() or any(repository.all(name) for name in TABLES):
                raise ValueError("只能恢复到空数据目录；现有记录不会被覆盖")
            marker = directory / "restore.pending.json"
            fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as handle:
                json.dump(raw, handle, ensure_ascii=False, allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            apply_pending(directory, repository, ledger)
        planner.input_sha = None
        return {"ok": True, "decisions": len(ledger.project_all())}

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
