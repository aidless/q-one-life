#!/usr/bin/env python3
"""Q-One Life 每日量化迭代入门脚本 —— 覆盖 10 个领域，写入首批观测。

作用：使用随包附带的指标目录（examples/metric-spec.json），为每个领域记录
一条有代表性的观测（共 10 条），再用「方向感知」的归一化方式为各领域打分。

用法：
    python3 examples/daily_quantified_iteration.py --data-dir /tmp/qone-life-data

说明：这是一个「起步示例」，每个领域只写一条处于合理中位区间的观测，
让维度向量分数变得有意义。请把这些示例数值替换成你自己的真实测量。
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 每个领域挑一个有代表性的指标（必须存在于 examples/metric-spec.json）。
# 元组含义：(领域, 指标, 数值, 下限, 上限)，数值为合理的真实读数。
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
    """记录每个领域的代表性观测，并对维度向量打分。"""
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

    # 把指标目录展开成 "领域:指标" 的集合，便于下面快速校验。
    spec_keys = set()
    for spec in specs:
        spec_keys.add(spec["domain"] + ":" + spec["metric"])

    # 写盘之前，先确认每个代表性指标都存在于目录中。
    for dom, metric, _v, _mn, _mx in REPRESENTATIVE:
        if f"{dom}:{metric}" not in spec_keys:
            raise SystemExit(f"Metric {dom}:{metric} not in catalog")

    # 延迟导入 qone_life：先把 src 目录加入搜索路径，使脚本在没有安装包时也能运行。
    sys.path.insert(0, str(repo_root / "src"))
    from qone_life.cli import main as cli_main

    # 用固定随机种子制造每天 ±10% 的合理波动，保证每次运行结果可复现。
    rng = random.Random(20261101)
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

    # 最后对整条维度向量打分。
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
