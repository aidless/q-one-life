"""单用户应用的 SQLite 持久化层，不需要任何云数据库。"""

from __future__ import annotations

import json
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

DOMAINS = {"work": "工作", "learning": "学习", "energy": "精力", "recovery": "恢复", "other": "其他", "finance": "财务", "health": "健康", "social": "社交", "emotion": "情绪", "environment": "环境"}
SCHEMA_VERSION = 1


class DatabaseVersionError(RuntimeError):
    """本地数据由不兼容的更新版本写入时抛出的异常。"""


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(prefix):
    return prefix + "-" + uuid4().hex


def timestamp(value):
    """把带时区的时间字符串规范化为 UTC ISO 格式；缺失时区则报错。"""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError) as exc:
        raise ValueError("时间必须包含时区") from exc


class Repository:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / "app.sqlite3"
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise DatabaseVersionError(
                    f"database schema {version} is newer than supported {SCHEMA_VERSION}"
                )
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS system_revisions(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS goals(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS suggestions(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS metrics(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            ''')
            if version < SCHEMA_VERSION:
                db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        """打开一次连接并在一个事务内 yield，结束时关闭连接。"""
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                db.execute("PRAGMA busy_timeout=15000")
                version = db.execute("PRAGMA user_version").fetchone()[0]
                if version > SCHEMA_VERSION:
                    raise DatabaseVersionError(
                        f"database schema {version} is newer than supported {SCHEMA_VERSION}"
                    )
                yield db
        finally:
            db.close()

    def _table(self, table):
        """校验表名合法，防止 SQL 注入。"""
        if table not in {"tasks", "metrics", "observations", "documents", "runs", "reviews", "goals", "suggestions", "system_revisions"}:
            raise ValueError("unknown record type")
        return table

    def all(self, table):
        table = self._table(table)
        with self.connect() as db:
            rows = db.execute(f"SELECT payload FROM {table} ORDER BY rowid DESC")
            return [json.loads(row[0]) for row in rows]

    def get(self, table, record_id):
        table = self._table(table)
        with self.connect() as db:
            row = db.execute(f"SELECT payload FROM {table} WHERE id=?", (record_id,)).fetchone()
        if row is None:
            raise KeyError("记录不存在")
        return json.loads(row[0])

    def put(self, table, payload):
        table = self._table(table)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        with self.connect() as db:
            db.execute(f"INSERT INTO {table}(id,payload) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                       (payload["id"], encoded))
        return payload

    def remove(self, table, record_id):
        table = self._table(table)
        with self.connect() as db:
            db.execute(f"DELETE FROM {table} WHERE id=?", (record_id,))

    def metric(self, raw):
        domain = raw.get("domain", "learning")
        name = str(raw.get("name", "")).strip()
        lo = float(raw.get("minimum", 0))
        hi = float(raw.get("maximum", 10))
        target_count = raw.get("target_count", 7)
        direction = raw.get("direction", "higher")
        if not name or len(name) > 80 or domain not in DOMAINS:
            raise ValueError("请填写有效指标名称与领域")
        # 上下限必须是有限数，且上限要大于下限。
        if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
            raise ValueError("指标最大值必须大于最小值，且均为有限数")
        if type(target_count) is not int or not 1 <= target_count <= 365:
            raise ValueError("期望记录数应为1到365的整数")
        if direction not in {"higher", "lower", "target"}:
            raise ValueError("指标方向无效")
        # 默认用区间中点；目标型指标改用自定义目标值。
        target = (lo + hi) / 2
        if direction == "target":
            target = float(raw.get("target", (lo + hi) / 2))
        if not math.isfinite(target) or not lo <= target <= hi:
            raise ValueError("目标值应位于指标范围内")
        return self.put("metrics", {"id": identifier("M"), "version": 1, "name": name,
            "domain": domain, "unit": str(raw.get("unit", "分"))[:20], "minimum": lo,
            "maximum": hi, "direction": direction, "target": target, "target_count": target_count,
            "created_at": now()})

    def observation(self, raw):
        metric = self.get("metrics", raw.get("metric_id"))
        value = float(raw.get("value"))
        if not math.isfinite(value) or not metric["minimum"] <= value <= metric["maximum"]:
            raise ValueError("记录值超出指标范围")
        observed = timestamp(raw.get("observed_at") or now())
        if datetime.fromisoformat(observed) > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("观察时间不能晚于当前时间")
        supersedes = raw.get("supersedes")
        if supersedes:
            old = self.get("observations", supersedes)
            if old["metric_id"] != metric["id"] or old.get("superseded_by"):
                raise ValueError("只能更正同一指标的当前记录")
        result = {"id": identifier("O"), "metric_id": metric["id"], "metric_version": metric["version"],
            "value": value, "observed_at": observed, "source": str(raw.get("source", "自我记录"))[:80],
            "note": str(raw.get("note", ""))[:2000], "created_at": now(), "supersedes": supersedes}
        # 更正观察与被更正行的更新必须在同一事务内完成。
        with self.connect() as db:
            if supersedes:
                current = json.loads(db.execute("SELECT payload FROM observations WHERE id=?", (supersedes,)).fetchone()[0])
                if current.get("superseded_by"):
                    raise ValueError("该观察已被更正")
                current["superseded_by"] = result["id"]
                db.execute("UPDATE observations SET payload=? WHERE id=?", (json.dumps(current, ensure_ascii=False), supersedes))
            db.execute("INSERT INTO observations VALUES(?,?)", (result["id"], json.dumps(result, ensure_ascii=False)))
        return result

    def scores(self, days=7):
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        # 只取未被更正为更新的观察，并且落在最近窗口内。
        observations = []
        for r in self.all("observations"):
            if r.get("superseded_by"):
                continue
            if datetime.fromisoformat(r["observed_at"]) < cutoff:
                continue
            observations.append(r)
        result = []
        for metric in reversed(self.all("metrics")):
            rows = [r for r in observations if r["metric_id"] == metric["id"]]
            values = []
            for row in rows:
                normalized = (row["value"] - metric["minimum"]) / (metric["maximum"] - metric["minimum"])
                if metric["direction"] == "lower":
                    normalized = 1 - normalized
                elif metric["direction"] == "target":
                    distance = max(metric["target"] - metric["minimum"], metric["maximum"] - metric["target"])
                    normalized = max(0, 1 - abs(row["value"] - metric["target"]) / distance)
                values.append(normalized)
            score = None
            if values:
                score = sum(values) / len(values)
            if rows:
                latest_row = max(rows, key=lambda r: r["observed_at"])
                latest_value = latest_row["value"]
            else:
                latest_value = None
            result.append(metric | {"n": len(rows), "coverage": min(1, len(rows) / metric["target_count"]),
                "score": score, "latest_value": latest_value, "rows": rows})
        return {"days": days, "metrics": result, "global_score": None,
                "observation_count": len(observations), "interpretation": "自定义指标的描述性记录，不代表人的价值"}

    def document(self, raw):
        title, content = str(raw.get("title", "")).strip(), str(raw.get("content", "")).strip()
        if not title or not content or len(title) > 150 or len(content) > 30000:
            raise ValueError("资料需有标题与正文，正文最多30000字")
        return self.put("documents", {"id": identifier("E"), "title": title, "content": content,
            "source": str(raw.get("source", "用户提供"))[:1000], "created_at": now(),
            "verified": False})

    def search(self, query, limit=3):
        words = re.findall(r"[a-zA-Z0-9]{2,}|[\u4e00-\u9fff]{2,}", query.lower())
        terms = set(words)
        # 中文按二元组切分，弥补没有分词器的情况。
        for word in words:
            if re.search(r"[\u4e00-\u9fff]", word):
                for i in range(len(word) - 1):
                    terms.add(word[i:i+2])
        ranked = []
        for row in self.all("documents"):
            text = (row["title"] + " " + row["content"]).lower()
            score = 0
            for term in terms:
                if term in text:
                    score += 1
            if score:
                ranked.append((score, row))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        results = []
        for _, row in ranked[:limit]:
            results.append({"id": row["id"], "title": row["title"], "source": row["source"],
                            "excerpt": row["content"][:1800], "verified": False})
        return results

    def goal(self, raw, goal_id=None):
        previous = {}
        if goal_id:
            previous = self.get("goals", goal_id)
        data = previous | raw
        if not isinstance(data.get("title"), str) or not isinstance(data.get("success_criterion"), str):
            raise ValueError("目标与完成标准必须为文本")  # noqa: TRY004 - 输入校验统一用 ValueError
        title, criterion = data["title"].strip(), data["success_criterion"].strip()
        priority, domain = data.get("priority", 3), data.get("domain", "learning")
        status = data.get("status", "active")
        if not title or len(title) > 150 or not criterion or len(criterion) > 1000 or domain not in DOMAINS:
            raise ValueError("请填写目标、可核查的完成标准和有效领域")
        if type(priority) is not int or not 1 <= priority <= 5 or status not in {"active", "paused", "completed"}:
            raise ValueError("目标优先级或状态无效")
        deadline = None
        if data.get("deadline"):
            deadline = timestamp(data["deadline"])
        return self.put("goals", {"id": goal_id or identifier("G"), "title": title, "success_criterion": criterion,
            "priority": priority, "domain": domain, "status": status,
            "deadline": deadline,
            "created_at": previous.get("created_at", now()), "updated_at": now()})
