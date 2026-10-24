"""SQLite persistence for the single-user application; no cloud database required."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

DOMAINS = {"work": "工作", "learning": "学习", "energy": "精力", "recovery": "恢复", "other": "其他"}


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(prefix):
    return prefix + "-" + uuid4().hex


def timestamp(value):
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
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS metrics(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            ''')
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                db.execute("PRAGMA busy_timeout=15000")
                yield db
        finally:
            db.close()

    @staticmethod
    def _table(table):
        if table not in {"tasks", "metrics", "observations", "documents", "runs", "reviews"}:
            raise ValueError("unknown record type")
        return table

    def all(self, table):
        table = self._table(table)
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute(f"SELECT payload FROM {table} ORDER BY rowid DESC")]

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
        lo, hi = float(raw.get("minimum", 0)), float(raw.get("maximum", 10))
        target_count = raw.get("target_count", 7)
        direction = raw.get("direction", "higher")
        if not name or len(name) > 80 or domain not in DOMAINS:
            raise ValueError("请填写有效指标名称与领域")
        if not all(math.isfinite(v) for v in (lo, hi)) or hi <= lo:
            raise ValueError("指标最大值必须大于最小值，且均为有限数")
        if type(target_count) is not int or not 1 <= target_count <= 365:
            raise ValueError("期望记录数应为1到365的整数")
        if direction not in {"higher", "lower", "target"}:
            raise ValueError("指标方向无效")
        target = float(raw.get("target", (lo + hi) / 2)) if direction == "target" else (lo + hi) / 2
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
        # An observation correction and the previous row update share a transaction.
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
        observations = [r for r in self.all("observations") if not r.get("superseded_by")
                        and datetime.fromisoformat(r["observed_at"]) >= cutoff]
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
            result.append(metric | {"n": len(rows), "coverage": min(1, len(rows) / metric["target_count"]),
                "score": sum(values) / len(values) if values else None,
                "latest_value": max(rows, key=lambda r: r["observed_at"])["value"] if rows else None,
                "rows": rows})
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
        for word in words:
            if re.search(r"[\u4e00-\u9fff]", word):
                terms.update(word[i:i+2] for i in range(len(word)-1))
        ranked = []
        for row in self.all("documents"):
            text = (row["title"] + " " + row["content"]).lower()
            score = sum(term in text for term in terms)
            if score:
                ranked.append((score, row))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [{"id": row["id"], "title": row["title"], "source": row["source"],
                 "excerpt": row["content"][:1800], "verified": False}
                for _, row in ranked[:limit]]
