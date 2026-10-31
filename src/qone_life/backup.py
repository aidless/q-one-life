"""校验备份，并在下次启动时恢复一次被中断的、指向空目录的还原操作。"""
import json
import math
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from qone_core.ledger import Ledger
from qone_core.service import DecisionService

from .repository import DOMAINS, SCHEMA_VERSION, timestamp

LEGACY_TABLES = {"tasks", "metrics", "observations", "documents", "runs", "reviews"}
V2_TABLES = LEGACY_TABLES | {"goals", "suggestions"}
TABLES = V2_TABLES | {"system_revisions"}


def validate_backup(raw):
    """全面校验一份备份的结构、事件可重放性与各数据表记录。

    校验分多层：先看备份格式与版本，再重放事件（确认状态迁移合法），
    然后逐表逐字段校验，最后校验人生模型版本链与任务对行动资源的引用。
    校验通过后返回补齐了所有表的字典；任一层不通过则抛出 ValueError。
    """
    if raw.get("format") not in {"q-one-backup-v1", "q-one-backup-v2", "q-one-backup-v3"} or not isinstance(
        raw.get("events"), list
    ):
        raise ValueError("备份格式无效")

    schema_version = raw.get("schema_version", 1)
    if type(schema_version) is not int or schema_version != SCHEMA_VERSION:
        raise ValueError("备份数据库版本与当前应用不兼容")

    # 不同备份格式要求出现的数据表集合不同。
    tables = raw.get("tables")
    expected_by_format = {
        "q-one-backup-v1": LEGACY_TABLES,
        "q-one-backup-v2": V2_TABLES,
        "q-one-backup-v3": TABLES,
    }
    expected = expected_by_format[raw["format"]]
    if not isinstance(tables, dict) or set(tables) != expected:
        raise ValueError("备份数据表不完整")

    # 把缺失的表补成空列表，保证后续可按固定键访问。
    complete_tables = {}
    for name in TABLES:
        complete_tables[name] = tables.get(name, [])
    tables = complete_tables

    json.dumps(raw, allow_nan=False)
    Ledger._verify_events(raw["events"])

    # 哈希完整性本身并不能证明应用层状态迁移合法，这里在临时目录里真正重放一遍事件。
    with TemporaryDirectory() as folder:
        service = DecisionService(Ledger(Path(folder) / "validate.jsonl"))
        for event in raw["events"]:
            payload = event["payload"]
            kind = event["type"]
            timestamp(event["ts"])
            if kind == "decision_created":
                service.create(payload)
            elif kind == "baseline_recorded":
                service.baseline(payload["decision_id"], payload["option_id"], payload.get("note", ""))
            elif kind == "recommendation_made":
                service.recommend(
                    payload["decision_id"], payload, payload.get("run_id"), payload.get("evidence_ids")
                )
            elif kind == "human_decision":
                service.decide(payload["decision_id"], payload["option_id"], payload.get("reason", ""))
            elif kind == "outcome_recorded":
                service.resolve(payload["decision_id"], payload["success"], payload.get("notes", ""))
            else:
                service.abandon(payload["decision_id"], payload["reason"])

    # 逐表检查：每条记录必须是带唯一 id 的对象，且时间字段合法。
    for rows in tables.values():
        if not isinstance(rows, list):
            raise ValueError("备份数据表格式无效")  # noqa: TRY004 - 输入校验统一用 ValueError（上层按单一类型捕获）
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"] or row["id"] in seen:
                raise ValueError("备份含无效或重复的记录ID")
            seen.add(row["id"])
            timestamp(row.get("created_at", row.get("started_at")))

    # 建立指标与观察的 id 索引，供后续交叉引用校验。
    metrics = {}
    for m in tables["metrics"]:
        metrics[m["id"]] = m
    observations = {}
    for o in tables["observations"]:
        observations[o["id"]] = o

    for metric in metrics.values():
        lo = metric["minimum"]
        hi = metric["maximum"]
        target = metric["target"]
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
        # 更正关系必须双向一致。
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

    goals = {}
    for g in tables["goals"]:
        goals[g["id"]] = g
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
        if (card["kind"] not in {"goal", "task", "review", "system"} or card["status"] not in {"active", "accepted", "dismissed"}
                or not all(isinstance(card.get(k), str) for k in ("title", "reason", "candidate_id", "revision", "source"))
                or type(card["minutes"]) is not int or not 5 <= card["minutes"] <= 480):
            raise ValueError("备份推荐无效")
        for key in ("first_step", "done_when"):
            if key in card and (not isinstance(card[key], str) or not card[key].strip() or len(card[key]) > 600):
                raise ValueError("备份推荐的行动说明无效")

    # 校验人生模型版本链。
    from .system import validate_revision_history
    validate_revision_history(tables['system_revisions'])

    versions = {}
    for r in tables['system_revisions']:
        versions[r['id']] = r

    from qone_core.life.model import fingerprint
    from qone_core.life.state import resource_key

    # 校验任务对行动定义与资源承诺的引用是否一致。
    for task in tables['tasks']:
        if task.get('system_action_id'):
            revision = versions.get(task.get('system_revision'))
            if revision is None:
                raise ValueError('任务引用的人生模型版本不存在')
            model = revision['model']
            actions = {}
            for a in model['actions']:
                actions[a['id']] = a
            resources = {}
            for r in model['resources']:
                resources[r['id']] = r
            action = actions.get(task['system_action_id'])
            if action is None or task.get('system_action_sha256') != fingerprint(action):
                raise ValueError('任务引用的行动定义不一致')
            expected = []
            for c in action.get('costs', []):
                amount = c['amount']
                # 区间成本取上限。
                if isinstance(amount, dict):
                    amount = amount['upper']
                expected.append({'resource_key': resource_key(resources[c['resource_id']]), 'amount': amount})
            if task.get('system_commitments') != expected:
                raise ValueError('任务承诺与事前行动资源定义不一致')
        for c in task.get('system_commitments', []):
            if (not isinstance(c, dict) or not isinstance(c.get('resource_key'), str)
                    or type(c.get('amount')) not in (int, float) or not math.isfinite(c['amount']) or c['amount'] < 0):
                raise ValueError('备份中的资源承诺无效')

    return tables


def apply_pending(directory, repository, ledger):
    """若存在待恢复标记文件，则把备份写入数据库与事件账本。

    待恢复文件是私有的，失败时保留（便于重试）；该操作在开始处理请求前是幂等的。
    """
    marker = directory / "restore.pending.json"
    if not marker.exists():
        return

    raw = json.loads(marker.read_text())
    tables = validate_backup(raw)

    with repository.connect() as db:
        for name in TABLES:
            rows = tables[name]
            # 系统版本表需要按旧到新的顺序写回。
            if name == "system_revisions":
                rows = reversed(rows)
            params = []
            for r in rows:
                params.append((r["id"], json.dumps(r, ensure_ascii=False, allow_nan=False)))
            db.executemany(
                f"INSERT INTO {name}(id,payload) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                params,
            )

        # 事件先写到临时文件并 fsync，再原子替换账本文件，避免半写。
        temporary = directory / "restore.events.tmp"
        chunks = []
        for e in raw["events"]:
            chunks.append(json.dumps(e, ensure_ascii=False) + "\n")
        temporary.write_text("".join(chunks))
        temporary.chmod(0o600)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, ledger.path)

    marker.unlink()
