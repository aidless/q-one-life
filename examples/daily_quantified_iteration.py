#!/usr/bin/env python3
"""Daily quantified iteration starter for Q-One Life — 10 domains, first observations.

Records one representative observation per domain (10 total) using the bundled
1183-metric catalog, then scores them with direction-aware normalization.

Usage:
    python3 examples/daily_quantified_iteration.py --data-dir /tmp/qone-life-data

This is a *starter*: it records exactly one observation per domain with a sensible
mid-range value so the dimension-vector score becomes meaningful. Replace the
values with your own real measurements.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# One representative metric per domain (must exist in examples/metric-spec.json).
# value = a plausible real-world reading; adjust to your own measurements.
REPRESENTATIVE = [
    ("health", "vitamin_a_intake", 1200, 0, 2000),
    ("finance", "dining_daily_amount", 350, 0, 1000),
    ("learning", "mathematics_hours", 4.8, 0, 8),
    ("work", "coding_hours", 4.8, 0, 8),
    ("social", "family_hours", 4.8, 0, 8),
    ("emotion", "interested_score", 3.6, 1, 5),
    ("environment", "pm25_index", 175, 0, 500),
    ("energy", "deep_sleep_minutes", 288, 0, 480),
    ("recovery", "meditation_minutes", 108, 0, 180),
    ("other", "screen_time_hours", 5.6, 0, 16),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily quantified iteration starter")
    parser.add_argument("--data-dir", default=".life-data", help="LifeStore data directory")
    parser.add_argument("--spec-file", default="examples/metric-spec.json", help="Metric spec JSON")
    parser.add_argument("--note", default="daily iteration starter", help="Observation note")
    parser.add_argument("--days", type=int, default=1,
                        help="number of consecutive days to record (default: 1)")
    args = parser.parse_args()

    if args.days < 1 or args.days > 90:
        raise SystemExit("--days must be between 1 and 90")

    repo_root = Path(__file__).resolve().parent.parent
    spec_path = (repo_root / args.spec_file).resolve()
    specs = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_keys = {s["domain"] + ":" + s["metric"] for s in specs}

    # Validate every representative exists in the catalog before writing anything.
    for dom, metric, _v, _mn, _mx in REPRESENTATIVE:
        if f"{dom}:{metric}" not in spec_keys:
            raise SystemExit(f"Metric {dom}:{metric} not in catalog")

    # Import lazily so the script can run without the package installed.
    import sys

    sys.path.insert(0, str(repo_root / "src"))
    from qone_life.cli import main as cli_main

    # Deterministic plausible day-over-day variation (+/- up to 10%).
    import random
    rng = random.Random(20261101)

    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone.utc)
    for day_offset in range(args.days):
        observed_at = (today - timedelta(days=day_offset)).strftime("%Y-%m-%dT12:00:00Z")
        for dom, metric, base_value, minimum, maximum in REPRESENTATIVE:
            drift = 1 + rng.uniform(-0.1, 0.1)
            value = round(base_value * drift, 2)
            value = min(maximum, max(minimum, value))
            argv = [
                "qone-life",
                "--data-dir", args.data_dir,
                "add-observation",
                "--domain", dom,
                "--metric", metric,
                "--value", str(value),
                "--minimum", str(minimum),
                "--maximum", str(maximum),
                "--source", "daily-iteration",
                "--note", args.note,
                "--observed-at", observed_at,
            ]
            sys.argv = argv
            cli_main()

    # Score the whole dimension vector.
    sys.argv = [
        "qone-life",
        "--data-dir", args.data_dir,
        "score",
        "--spec-file", str(spec_path),
    ]
    cli_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
