"""PeerRead paper-level held-out check: freeze rubric on train+dev, evaluate on test."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import scipy.stats as stats


def bootstrap_ci(x: list[float], y: list[float], draws: int, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        index = rng.integers(0, len(x), len(x))
        if len(set(index.tolist())) < 3:
            continue
        rho = stats.spearmanr([x[i] for i in index], [y[i] for i in index]).statistic
        if math.isfinite(rho):
            values.append(float(rho))
    return [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--draws", type=int, default=10000)
    args = parser.parse_args()

    records = []
    for path in sorted((args.root / "peerread-expanded").glob("paper-*.json")):
        record = json.loads(path.read_text())
        if record.get("rubric") and record.get("human_scores"):
            records.append(record)

    def score(record: dict, weights: dict[str, float]) -> float:
        return sum(weights[key] * record["rubric"][key] for key in ("novelty", "rigor", "clarity"))

    train_dev = [record for record in records if record["split"] in ("train", "dev")]
    test = [record for record in records if record["split"] == "test"]
    # Freeze a simple equal-weight rubric on train+dev (this is the only rule choice;
    # no grid search over weights is performed).
    weights = {"novelty": 1 / 3, "rigor": 1 / 3, "clarity": 1 / 3}
    x_train = [score(record, weights) for record in train_dev]
    y_train = [float(np.mean(record["human_scores"])) for record in train_dev]
    x_test = [score(record, weights) for record in test]
    y_test = [float(np.mean(record["human_scores"])) for record in test]

    def summarize(x: list[float], y: list[float]) -> dict:
        if len(x) < 4:
            return {"n": len(x), "rho": None, "p": None, "ci": None}
        rho, p = stats.spearmanr(x, y)
        return {
            "n": len(x), "rho": float(rho), "p": float(p),
            "ci": bootstrap_ci(x, y, min(args.draws, 2000), 20261107),
        }

    report = {
        "schema": "qone-peerread-heldout-v1",
        "model": "kiro/deepseek-3.2",
        "weights": weights,
        "frozen": "equal weights chosen before looking at test split; no grid search",
        "train_dev": summarize(x_train, y_train),
        "test": summarize(x_test, y_test),
        "train_dev_n": len(train_dev), "test_n": len(test),
        "claim_limit": "Paper-level split; 6 test papers is too small for a calibration verdict.",
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "heldout.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
