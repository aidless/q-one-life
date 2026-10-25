"""Validate backups and recover an interrupted, empty-space restore on next launch."""
import json
import math
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from qone_core.ledger import Ledger
from qone_core.service import DecisionService
from .repository import DOMAINS, timestamp

LEGACY_TABLES = {"tasks", "metrics", "observations", "documents", "runs", "reviews"}
TABLES = LEGACY_TABLES | {"goals", "suggestions"}


def validate_backup(raw):
    if raw.get("format") not in {"q-one-backup-v1", "q-one-backup-v2"} or not isinstance(raw.get("events"), list):
        raise ValueError("备份格式无效")
    tables = raw.get("tables")
    expected = LEGACY_TABLES if raw["format"] == "q-one-backup-v1" else TABLES
    if not isinstance(tables, dict) or set(tables) != expected:
        raise ValueError("备份数据表不完整")
    tables = {name: tables.get(name, []) for name in TABLES}
    json.dumps(raw, allow_nan=False)
    Ledger._verify_events(raw["events"])
    # Hash integrity alone does not establish valid application state transitions.
    with TemporaryDirectory() as folder:
        service = DecisionService(Ledger(Path(folder) / "validate.jsonl"))
        for event in raw["events"]:
            p, kind = event["payload"], event["type"]
            timestamp(event["ts"])
            if kind == "decision_created":
                service.create(p)
            elif kind == "baseline_recorded":
                service.baseline(p["decision_id"], p["option_id"], p.get("note", ""))
            elif kind == "recommendation_made":
                service.recommend(p["decision_id"], p, p.get("run_id"), p.get("evidence_ids"))
            elif kind == "human_decision":
                service.decide(p["decision_id"], p["option_id"], p.get("reason", ""))
            elif kind == "outcome_recorded":
                service.resolve(p["decision_id"], p["success"], p.get("notes", ""))
            else:
                service.abandon(p["decision_id"], p["reason"])
    for name, rows in tables.items():
        if not isinstance(rows, list):
            raise ValueError("备份数据表格式无效")
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"] or row["id"] in seen:
                raise ValueError("备份含无效或重复的记录ID")
            seen.add(row["id"])
            timestamp(row.get("created_at", row.get("started_at")))
    metrics = {m["id"]: m for m in tables["metrics"]}
    observations = {o["id"]: o for o in tables["observations"]}
    for metric in metrics.values():
        lo, hi, target = (metric[k] for k in ("minimum", "maximum", "target"))
        if (not all(type(v) in (int, float) and math.isfinite(v) for v in (lo, hi, target))
                or hi <= lo or not lo <= target <= hi or metric["direction"] not in {"higher", "lower", "target"}
                or type(metric["target_count"]) is not int or not 1 <= metric["target_count"] <= 365
                or metric["domain"] not in DOMAINS or not isinstance(metric["name"], str)
                or not isinstance(metric["unit"], str) or metric["version"] != 1):
            raise ValueError("备份指标定义无效")
    for row in observations.values():
        m = metrics.get(row["metric_id"])
        value = row["value"]
        if not m or type(value) not in (int, float) or not math.isfinite(value) or not m["minimum"] <= value <= m["maximum"]:
            raise ValueError("备份观察记录无效")
        timestamp(row["observed_at"])
        for key, reverse in (("supersedes", "superseded_by"), ("superseded_by", "supersedes")):
            if row.get(key):
                other = observations.get(row[key])
                if not other or other["metric_id"] != m["id"] or other.get(reverse) != row["id"]:
                    raise ValueError("备份更正记录的关联不完整")
    for task in tables["tasks"]:
        if not isinstance(task["title"], str) or type(task["done"]) is not bool or task["domain"] not in DOMAINS:
            raise ValueError("备份任务无效")
        if task.get("deadline"):
            timestamp(task["deadline"])
    for document in tables["documents"]:
        if not all(isinstance(document.get(k), str) for k in ("title", "content", "source")):
            raise ValueError("备份资料无效")
    for review in tables["reviews"]:
        if not isinstance(review["text"], str) or review["days"] not in (7, 30, 90) or not isinstance(review["snapshot"], dict):
            raise ValueError("备份复盘无效")
    goals = {g["id"]: g for g in tables["goals"]}
    for goal in goals.values():
        if (not isinstance(goal["title"], str) or not isinstance(goal["success_criterion"], str)
                or goal["domain"] not in DOMAINS or goal["status"] not in {"active", "paused", "completed"}
                or type(goal["priority"]) is not int or not 1 <= goal["priority"] <= 5):
            raise ValueError("备份目标无效")
        if goal.get("deadline"):
            timestamp(goal["deadline"])
    for task in tables["tasks"]:
        if task.get("goal_id") and task["goal_id"] not in goals:
            raise ValueError("备份任务引用的目标不存在")
        if "estimate_minutes" in task and (type(task["estimate_minutes"]) is not int or not 5 <= task["estimate_minutes"] <= 480):
            raise ValueError("备份任务时长无效")
    for card in tables["suggestions"]:
        if (card["kind"] not in {"goal", "task", "review"} or card["status"] not in {"active", "accepted", "dismissed"}
                or not all(isinstance(card.get(k), str) for k in ("title", "reason", "candidate_id", "revision", "source"))
                or type(card["minutes"]) is not int or not 5 <= card["minutes"] <= 480):
            raise ValueError("备份推荐无效")
        for key in ("first_step", "done_when"):
            if key in card and (not isinstance(card[key], str) or not card[key].strip() or len(card[key]) > 600):
                raise ValueError("备份推荐的行动说明无效")
    return tables


def apply_pending(directory, repository, ledger):
    """Pending file is private and retained on failure; idempotent before serving requests."""
    marker = directory / "restore.pending.json"
    if not marker.exists():
        return
    raw = json.loads(marker.read_text())
    tables = validate_backup(raw)
    with repository.connect() as db:
        for name in TABLES:
            db.executemany(f"INSERT INTO {name}(id,payload) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                           [(r["id"], json.dumps(r, ensure_ascii=False, allow_nan=False)) for r in tables[name]])
        temporary = directory / "restore.events.tmp"
        temporary.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in raw["events"]))
        temporary.chmod(0o600)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, ledger.path)
    marker.unlink()
