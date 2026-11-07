"""在云端从四个 boards CSV 的 verdict 列独立重数 AJB 3,200 板。

不依赖 p4_ajb_counts.json；输出逐臂计数、总数、READABLE 数与 SHA-256。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "q-one-cloud-ajb-recount-v1"


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True, nargs="+")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    arms: dict[str, dict] = {}
    grand = Counter()
    for raw in args.inputs:
        path = Path(raw).expanduser().resolve()
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        counts = Counter(row["verdict"].strip() for row in rows)
        arms[path.name] = {
            "rows": len(rows),
            "verdicts": dict(sorted(counts.items())),
            "sha256": _sha256(path),
        }
        grand.update(counts)

    verdicts = dict(sorted(grand.items()))
    total = sum(grand.values())
    readable = grand.get("READABLE", 0)
    result = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "arms": arms,
        "total_boards": total,
        "verdicts": verdicts,
        "readable": readable,
        "status": "passed" if total == 3200 and readable == 0 else "failed",
    }
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "total_boards": total,
        "verdicts": verdicts,
        "readable": readable,
        "receipt": str(out),
        "receipt_sha256": _sha256(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
