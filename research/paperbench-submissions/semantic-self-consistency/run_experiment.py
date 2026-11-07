#!/usr/bin/env python3
"""Run the Semantic Self-Consistency reproduction on the configured benchmark.

Examples:
  # Mock smoke (no paid models):
  python run_experiment.py --lm mock --dataset svamp --limit 2 --out results/mock.json

  # Real model (OpenAI-compatible):
  OPENAI_API_KEY=... python run_experiment.py --lm openai --model gpt-4o-mini --dataset svamp
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic Self-Consistency reproduction runner")
    parser.add_argument("--lm", choices=["mock", "openai"], default="openai")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--datasets", default="aqua_rat,svamp,strategyqa")
    parser.add_argument("--limit", type=int, default=None, help="Limit samples per dataset")
    parser.add_argument("--out", default="results/run.json")
    args = parser.parse_args()

    if args.lm == "mock":
        from src.core import MockLM
        lm = MockLM()
    else:
        from src.core import OpenAILLM
        lm = OpenAILLM(args.model, os.environ["OPENAI_API_KEY"])

    from src.core import DATASETS, run_benchmark

    out: dict = {}
    for name in [d.strip() for d in args.datasets.split(",")]:
        cfg = DATASETS[name]
        samples = cfg["loader"]()
        if args.limit is not None:
            samples = samples[: args.limit]
        out[name] = run_benchmark(name, samples, lm, cfg["featurizer"])

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k: (v.get("methods", {}).get("sc_baseline") or {}) for k, v in out.items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
