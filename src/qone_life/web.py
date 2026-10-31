"""Q-One: a local, single-user Chinese workspace backed by real model adapters."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import locale as system_locale
import os
import secrets
import tempfile
import threading
import base64
from contextlib import asynccontextmanager
from hmac import compare_digest
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from qone_agent.runtime import ProviderError, is_loopback, public_context, run_model
from qone_core.ledger import Ledger, LedgerError
from qone_core.report import build_report
from qone_core.service import DecisionService
from . import __version__
from .planner import Planner
from .plan_runtime import generate_plan
from .backup import TABLES, apply_pending, validate_backup
from .encrypted_backup import (
    BackupCryptoError,
    decode_recovery_key,
    decrypt_backup,
    encode_recovery_key,
    encrypt_backup,
    inspect_backup,
)
from .repository import (
    DOMAINS,
    DatabaseVersionError,
    Repository,
    SCHEMA_VERSION,
    identifier,
    now,
    timestamp,
)

STATIC = Path(__file__).parent / "static"
DEFAULTS = {
    "auto_recommend_enabled": True, "auto_recommend_provider": "local",
    "auto_recommend_interval_minutes": 360, "daily_available_minutes": 90,
    "language": "system", "onboarding_complete": False,
    "ollama_url": "http://127.0.0.1:11434", "ollama_model": "qwen3:8b",
    "cloud_url": "", "cloud_model": "", "cloud_key": "",
    "laya_checkpoint": "convaiinnovations/laya-multilingual",
    "laya_revision": "1720e3e3357cfe1e281542e223f8273b0890ca34",
    "laya_model_path": "", "laya_device": "cpu", "default_provider": "local",
}


def _error_response(
    message: str,
    code: str,
    status_code: int,
    *,
    retryable: bool = False,
    request_id: str | None = None,
):
    identifier = request_id or uuid4().hex
    return JSONResponse(
        {
            "detail": message,
            "error": {
                "code": code,
                "retryable": retryable,
                "request_id": identifier,
                "params": {},
            },
        },
        status_code=status_code,
        headers={"X-Request-ID": identifier},
    )


def create_app(
    data_dir=None,
    *,
    model_runner=run_model,
    plan_runner=generate_plan,
    capability: str | None = None,
    control_token: str | None = None,
    cloud_key: str | None = None,
    secret_managed: bool = False,
    default_locale: str | None = None,
    local_model_url: str | None = None,
    local_model_name: str | None = None,
    local_model_token: str | None = None,
):
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

    app = FastAPI(lifespan=lifespan, title="Q-One 人生系统", version=__version__, docs_url="/api/docs", redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])
    app.state.repository, app.state.ledger = repository, ledger

    cloud_key_override = cloud_key
    local_model_override = bool(local_model_url and local_model_name and local_model_token)

    def resolved_language(value: dict):
        selected = value.get("language", "system")
        if selected in {"zh-CN", "en-US"}:
            return selected
        candidate = default_locale
        if not candidate:
            candidate = os.environ.get("LC_ALL") or os.environ.get("LANG")
        if not candidate:
            try:
                candidate = system_locale.getlocale()[0]
            except (ValueError, TypeError):
                candidate = None
        return "en-US" if str(candidate or "").lower().startswith("en") else "zh-CN"

    def settings():
        saved = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        value = DEFAULTS | saved
        # A pre-1.0 installation already has settings and should not be sent
        # through first-run setup merely because the new flag did not exist.
        if settings_path.exists() and "onboarding_complete" not in saved:
            value["onboarding_complete"] = True
        value["resolved_language"] = resolved_language(value)
        if cloud_key_override is not None:
            value["cloud_key"] = cloud_key_override
        elif os.environ.get("QONE_CLOUD_API_KEY"):
            value["cloud_key"] = os.environ["QONE_CLOUD_API_KEY"]
        if local_model_override:
            value["local_url"] = local_model_url
            value["local_model"] = local_model_name
            value["local_token"] = local_model_token
        return value

    def public_settings():
        value = settings()
        value["cloud_key_set"] = bool(value.pop("cloud_key", ""))
        local_url = value.pop("local_url", None)
        local_token = value.pop("local_token", None)
        value["local_model_available"] = bool(local_url and local_token and value.get("local_model"))
        value["secret_management"] = "os_keychain" if secret_managed else "local_settings"
        value["laya_installed"] = importlib.util.find_spec("laya") is not None
        return value

    def save_settings(raw):
        if secret_managed and ("cloud_key" in raw or raw.get("clear_cloud_key")):
            raise ValueError("桌面版接口密钥由系统密钥存储管理，请从设置页重新保存")
        current = settings()
        current.pop("resolved_language", None)
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
                if key == "language":
                    if raw[key] not in {"system", "zh-CN", "en-US"}:
                        raise ValueError("界面语言无效")
                    current[key] = raw[key]
                    continue
                if key == "onboarding_complete":
                    if type(raw[key]) is not bool:
                        raise ValueError("首次设置状态必须为开或关")
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
        if current["auto_recommend_provider"] not in {"local", "ollama", "laya"}:
            raise ValueError("自动推荐请选择内置模型、本地Ollama或Laya")
        if current["default_provider"] not in {"local", "ollama", "laya", "cloud"}:
            raise ValueError("默认模型无效")
        if current["laya_device"] not in {"cpu", "cuda"}:
            raise ValueError("Laya设备仅支持cpu或cuda")
        with lock:
            fd, temporary = tempfile.mkstemp(prefix="settings-", dir=directory)
            try:
                if os.name != "nt":
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
        request_id = uuid4().hex
        request.state.qone_request_id = request_id
        if capability is not None and (
            request.url.path == "/api" or request.url.path.startswith("/api/")
        ):
            supplied = request.headers.get("x-qone-capability", "")
            if not compare_digest(supplied, capability):
                return _error_response(
                    "本地客户端凭据无效",
                    "DESKTOP_CAPABILITY_REQUIRED",
                    403,
                    request_id=request_id,
                )
        if request.url.path.startswith("/api/desktop/"):
            supplied_control = request.headers.get("x-qone-control", "")
            if control_token is None or not compare_digest(supplied_control, control_token):
                return _error_response(
                    "此操作只能由 Q-One 桌面主进程发起",
                    "DESKTOP_CONTROL_REQUIRED",
                    403,
                    request_id=request_id,
                )
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and urlparse(origin).netloc != request.headers.get("host"):
                return _error_response(
                    "只接受当前页面发出的操作",
                    "ORIGIN_REJECTED",
                    403,
                    request_id=request_id,
                )
            if request.headers.get("x-qone-client") != "web":
                return _error_response(
                    "缺少本地客户端标识",
                    "CLIENT_HEADER_REQUIRED",
                    403,
                    request_id=request_id,
                )
            if request.method != "DELETE" and "application/json" not in request.headers.get("content-type", ""):
                return _error_response(
                    "请求需为JSON格式",
                    "JSON_CONTENT_TYPE_REQUIRED",
                    415,
                    request_id=request_id,
                )
            body = await request.body()
            if len(body) > 4 * 1024 * 1024:
                return _error_response(
                    "单次数据不能超过4MB",
                    "REQUEST_TOO_LARGE",
                    413,
                    request_id=request_id,
                )
        response = await call_next(request)
        if request.method in {"POST", "PATCH", "PUT", "DELETE"} and response.status_code < 400:
            planner.notify()
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(ValueError)
    async def bad_value(request, exc):
        return _error_response(
            str(exc),
            "INVALID_REQUEST",
            400,
            request_id=getattr(request.state, "qone_request_id", None),
        )

    @app.exception_handler(TypeError)
    async def bad_type(request, exc):
        return _error_response(
            "字段类型无效，请检查数值与文本",
            "INVALID_FIELD_TYPE",
            400,
            request_id=getattr(request.state, "qone_request_id", None),
        )

    @app.exception_handler(KeyError)
    async def not_found(request, exc):
        return _error_response(
            "记录不存在",
            "RECORD_NOT_FOUND",
            404,
            request_id=getattr(request.state, "qone_request_id", None),
        )

    @app.exception_handler(LedgerError)
    async def corrupt_ledger(request, exc):
        return _error_response(
            "决策记录完整性校验失败，请从本地备份检查恢复",
            "LEDGER_CORRUPT",
            409,
            request_id=getattr(request.state, "qone_request_id", None),
        )

    @app.exception_handler(RequestValidationError)
    async def malformed(request, exc):
        return _error_response(
            "提交的数据格式不正确，请检查必填字段",
            "REQUEST_VALIDATION_FAILED",
            422,
            request_id=getattr(request.state, "qone_request_id", None),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        codes = {
            401: "AUTHENTICATION_REQUIRED",
            403: "REQUEST_FORBIDDEN",
            404: "RECORD_NOT_FOUND",
            409: "CONFLICT",
            413: "REQUEST_TOO_LARGE",
            415: "UNSUPPORTED_CONTENT_TYPE",
            422: "REQUEST_VALIDATION_FAILED",
            429: "RATE_LIMITED",
            502: "MODEL_PROVIDER_FAILED",
            503: "SERVICE_UNAVAILABLE",
        }
        return _error_response(
            str(exc.detail),
            codes.get(exc.status_code, "REQUEST_FAILED"),
            exc.status_code,
            retryable=exc.status_code in {429, 502, 503},
            request_id=getattr(request.state, "qone_request_id", None),
        )

    @app.exception_handler(DatabaseVersionError)
    async def unsupported_database(request, exc):
        return _error_response(
            "本地数据由更新版本的 Q-One 写入，请安装更新版本后再打开",
            "DATABASE_VERSION_UNSUPPORTED",
            409,
            request_id=getattr(request.state, "qone_request_id", None),
        )

    @app.exception_handler(BackupCryptoError)
    async def bad_backup_crypto(request, exc):
        return _error_response(
            str(exc),
            "BACKUP_INVALID_OR_WRONG_KEY",
            400,
            request_id=getattr(request.state, "qone_request_id", None),
        )

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
        return {"status": "ok", "version": __version__, "ledger_events": ledger.verify(), "storage": "local"}

    @app.get("/api/bootstrap")
    def bootstrap(days: int = 7):
        if days not in {7, 30, 90}:
            raise ValueError("请选择7、30或90天窗口")
        with lock:
            sync_tasks()
            public = public_settings()
            return {"goals": repository.all("goals"), "planner": planner.state(), "decisions": public_decisions(), "tasks": repository.all("tasks"),
                "scores": repository.scores(days), "report": build_report(ledger), "domains": DOMAINS,
                "documents": [{k: v for k, v in row.items() if k != "content"} for row in repository.all("documents")],
                "reviews": repository.all("reviews"), "runs": repository.all("runs")[:30],
                "settings": public, "demo": bool(os.environ.get("QONE_DEMO")),
                "locale": public["resolved_language"], "version": __version__}

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
        if provider == "local":
            url = config.get("local_url", "")
            model = config.get("local_model", "")
        elif provider == "cloud":
            url = config.get("cloud_url", "")
            model = config.get("cloud_model", "")
        else:
            url = config.get("ollama_url", "")
            model = config.get("ollama_model", "")
        binding = {"context": context, "provider": provider, "url": url,
            "model": model, "revision": config.get("laya_revision")}
        return hashlib.sha256(json.dumps(binding, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    @app.post("/api/decisions/{decision_id}/preview")
    def preview(decision_id: str, raw: dict):
        state = ledger.get(decision_id)
        evidence = repository.search(state["question"] + " " + state["success_criterion"]) if raw.get("use_evidence", True) else []
        context = public_context(state, evidence)
        config = settings()
        provider = raw.get("provider", config["default_provider"])
        if provider == "local":
            url = config.get("local_url", "")
            model = config.get("local_model", "")
            endpoint = "本机内置模型"
        elif provider == "cloud":
            url = config.get("cloud_url", "")
            model = config.get("cloud_model", "")
            endpoint = url
        elif provider == "laya":
            url = ""
            model = config["laya_checkpoint"]
            endpoint = "本机Laya进程"
        else:
            url = config["ollama_url"]
            model = config["ollama_model"]
            endpoint = url
        return {"context": context, "remote": provider in {"ollama", "cloud"} and not is_loopback(url),
                "evidence_ids": [row["id"] for row in evidence], "provider": provider,
                "endpoint": endpoint, "model": model,
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
        endpoint = (
            config.get("local_url", "")
            if provider == "local"
            else config.get("cloud_url", "")
            if provider == "cloud"
            else config["ollama_url"]
            if provider == "ollama"
            else ""
        )
        remote = provider in {"ollama", "cloud"} and not is_loopback(endpoint)
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

    @app.post("/api/system/observations", status_code=201)
    def record_system_observations(raw: dict):
        with planner.lock:
            result = planner.system.record_observations(raw)
            if not result['unchanged']:
                planner.input_sha = None
            return result

    @app.post("/api/system/outcomes/preview")
    def preview_outcome(raw: dict):
        with planner.lock:
            return planner.system.preview_outcome(raw)

    @app.post("/api/system/outcomes", status_code=201)
    def record_outcome(raw: dict):
        with planner.lock:
            result = planner.system.record_outcome(raw)
            if not result['unchanged']:
                planner.input_sha = None
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
            return planner.system.replay(raw.get('candidate_calibration'))

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

    @app.get("/api/scores")
    def read_scores(days: int = 7):
        return repository.scores(days)

    @app.get("/api/iterate")
    def read_iterate(days: int = 7):
        """Per-day direction-aware dimension scores, deltas, and trends."""
        from .iteration import daily_iteration
        from .models import MetricSpec, Observation

        metrics = repository.all("metrics")
        specs = tuple(
            MetricSpec(
                domain=m["domain"], metric=m["name"], minimum=m["minimum"],
                maximum=m["maximum"], direction=m["direction"],
                unit=m.get("unit", ""), target=m.get("target"),
                target_count=m.get("target_count", 1),
            )
            for m in metrics
        )
        observations = [
            Observation(
                observation_id=r["id"], domain=m["domain"], metric=m["name"],
                value=r["value"], minimum=m["minimum"], maximum=m["maximum"],
                observed_at=r["observed_at"], source=r.get("source", ""),
                note=r.get("note", ""),
            )
            for r in repository.all("observations")
            if not r.get("superseded_by")
            for m in [next((x for x in metrics if x["id"] == r["metric_id"]), None)]
            if m is not None
        ]
        return daily_iteration(observations, specs, window_days=days)

    @app.get("/api/suggest")
    def read_suggest(threshold: float = 0.5):
        """Actionable next-step suggestions per domain, direction-aware."""
        from .models import MetricSpec, Observation
        from .suggestion import suggest_improvements

        metrics = repository.all("metrics")
        specs = tuple(
            MetricSpec(
                domain=m["domain"], metric=m["name"], minimum=m["minimum"],
                maximum=m["maximum"], direction=m["direction"],
                unit=m.get("unit", ""), target=m.get("target"),
                target_count=m.get("target_count", 1),
            )
            for m in metrics
        )
        observations = [
            Observation(
                observation_id=r["id"], domain=m["domain"], metric=m["name"],
                value=r["value"], minimum=m["minimum"], maximum=m["maximum"],
                observed_at=r["observed_at"], source=r.get("source", ""),
                note=r.get("note", ""),
            )
            for r in repository.all("observations")
            if not r.get("superseded_by")
            for m in [next((x for x in metrics if x["id"] == r["metric_id"]), None)]
            if m is not None
        ]
        return suggest_improvements(observations, specs, threshold=threshold)

    @app.get("/api/settings")
    def read_settings():
        return public_settings()

    @app.post("/api/settings")
    def update_settings(raw: dict):
        return save_settings(raw)

    @app.get("/api/providers")
    def providers():
        config = settings()
        local = {"available": False, "model": config.get("local_model", ""), "error": None}
        local_url = config.get("local_url", "")
        local_token = config.get("local_token", "")
        if local_url and local_token and is_loopback(local_url):
            try:
                parsed = urlparse(local_url)
                health_url = f"{parsed.scheme}://{parsed.netloc}/health"
                with httpx.Client(timeout=3, trust_env=False) as client:
                    response = client.get(health_url, headers={"Authorization": "Bearer " + local_token})
                    response.raise_for_status()
                    local.update(available=True)
            except (httpx.HTTPError, ValueError, KeyError):
                local["error"] = "内置模型服务尚未就绪"
        elif not local_url:
            local["error"] = "尚未下载内置模型"
        ollama = {"available": False, "models": [], "error": None}
        if is_loopback(config["ollama_url"]):
            try:
                with httpx.Client(timeout=3, trust_env=False) as client:
                    response = client.get(config["ollama_url"].rstrip("/") + "/api/tags")
                    response.raise_for_status()
                    ollama.update(available=True, models=[m["name"] for m in response.json().get("models", [])])
            except (httpx.HTTPError, ValueError, KeyError):
                ollama["error"] = "本地Ollama尚未连接"
        return {"local": local, "ollama": ollama, "laya": {"installed": importlib.util.find_spec("laya") is not None,
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
            result = {"format": "q-one-backup-v3", "schema_version": SCHEMA_VERSION,
                "created_at": now(), "events": ledger.events(),
                "tables": {name: repository.all(name) for name in TABLES}}
        return JSONResponse(result, headers={"Content-Disposition": 'attachment; filename="q-one-private-backup.json"'})

    def backup_payload():
        return {"format": "q-one-backup-v3", "schema_version": SCHEMA_VERSION,
            "created_at": now(), "events": ledger.events(),
            "tables": {name: repository.all(name) for name in TABLES}}

    @app.post("/api/desktop/backup/export")
    def desktop_backup_export(raw: dict):
        try:
            data_key = base64.b64decode(str(raw.get("data_key", "")), validate=True)
            recovery_key = base64.b64decode(str(raw.get("recovery_key", "")), validate=True)
        except (ValueError, TypeError) as exc:
            raise BackupCryptoError("备份密钥编码无效") from exc
        if len(data_key) != 32 or len(recovery_key) != 32:
            raise BackupCryptoError("备份密钥必须为 256 位")
        with lock, planner.lock:
            payload = backup_payload()
        return encrypt_backup(payload, data_key, recovery_key)

    @app.post("/api/desktop/backup/inspect")
    def desktop_backup_inspect(raw: dict):
        return inspect_backup(raw)

    @app.post("/api/desktop/backup/decrypt")
    def desktop_backup_decrypt(raw: dict):
        container = raw.get("container")
        if isinstance(raw.get("recovery_key_text"), str):
            recovery_key = decode_recovery_key(raw["recovery_key_text"])
        else:
            try:
                recovery_key = base64.b64decode(str(raw.get("recovery_key", "")), validate=True)
            except (ValueError, TypeError) as exc:
                raise BackupCryptoError("恢复密钥编码无效") from exc
        if not isinstance(container, dict):
            raise BackupCryptoError("备份文件无效")
        return decrypt_backup(container, recovery_key)

    @app.post("/api/desktop/backup/recovery-key")
    def desktop_backup_recovery_key(raw: dict):
        try:
            key = base64.b64decode(str(raw.get("key", "")), validate=True)
        except (ValueError, TypeError) as exc:
            raise BackupCryptoError("恢复密钥编码无效") from exc
        return {"recovery_key": encode_recovery_key(key)}

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

    @app.get("/advanced")
    def advanced():
        return FileResponse(STATIC / "advanced.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
