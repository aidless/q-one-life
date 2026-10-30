"""
bds_evaluator.py — Compute Behavior Drift Score (BDS) per scenario across
snapshots.

Reads `data/raw/{model}___{snapshot}.jsonl` files emitted by
`run_protocol.py`, then computes the **per-scenario, per-model BDS** as
defined in protocol.md §3.2.

Output: `data/bds_table.json` and a wide CSV `data/bds_table.csv` for
spreadsheet inspection.

Usage:
    python bds_evaluator.py --in data/raw --out data
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


# ----------------------------- Tokenizer -------------------------------

def _tokenize_simple(text: str) -> List[str]:
    """Whitespace + lowercase tokenization for BDS purposes — agnostic of
    the model under test (so we are NOT measuring tokenizer drift here).
    """
    if not text:
        return []
    return [
        tok.lower().strip(".,;:!?'\"()[]{}") for tok in text.split()
        if tok and len(tok) > 1
    ]


def _build_vocab(snap_outputs: Dict[str, List[str]], top_k: int = 10_000
                 ) -> Dict[str, int]:
    """Build a fixed-size vocabulary from the union of tokens across the
    three snapshots, taking the top-K most frequent.
    """
    counter: Counter = Counter()
    for outs in snap_outputs.values():
        for o in outs:
            counter.update(_tokenize_simple(o))
    most_common = counter.most_common(top_k)
    return {tok: idx for idx, (tok, _) in enumerate(most_common)}


def _histogram(tokens: List[str], vocab: Dict[str, int]) -> np.ndarray:
    p = np.full(len(vocab), 1e-5, dtype=np.float64)  # Laplace smoothing
    for tok in tokens:
        if tok in vocab:
            p[vocab[tok]] += 1.0
    p = p / p.sum()
    return p


def _kl(p: np.ndarray, q: np.ndarray) -> float:
    return float(np.sum(p * np.log(p / q)))


def _bds(snap_outputs: Dict[str, List[str]]) -> float:
    """BDS over the 3 snapshots — average KL across the 3 unordered pairs.
    """
    vocab = _build_vocab(snap_outputs)
    if len(vocab) < 5:
        # Not enough vocab to compute a meaningful drift.
        return 0.0
    hists = {
        snap: _histogram(
            sum(
                [_tokenize_simple(o) for o in outs],
                [],
            ),
            vocab,
        )
        for snap, outs in snap_outputs.items()
    }
    if len(hists) < 2:
        return 0.0
    kls = []
    for a, b in combinations(hists.keys(), 2):
        kls.append(_kl(hists[a], hists[b]))
    return float(np.mean(kls))


# --------------------------- Main Driver -------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", type=Path,
                        default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    files = sorted(args.inp.glob("*__*.jsonl"))
    if not files:
        raise SystemExit(
            f"no raw files in {args.inp}; run run_protocol.py first"
        )

    # group: model_alias -> snapshot -> {scenario_id -> [text, ...]}
    grouped: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    manifest_summary: List[Tuple[str, Path]] = []
    for f in files:
        if "_manifest.json" in f.name:
            continue
        # filename: {model}__{snapshot}.jsonl
        parts = f.stem.split("__")
        if len(parts) != 2:
            print(f"   skipping malformed filename: {f}")
            continue
        model_alias, snapshot = parts
        manifest_summary.append((f"{model_alias}__{snapshot}", f))
        if model_alias not in grouped:
            grouped[model_alias] = {}
        if snapshot not in grouped[model_alias]:
            grouped[model_alias][snapshot] = {}
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                sid = rec["scenario_id"]
                if sid not in grouped[model_alias][snapshot]:
                    grouped[model_alias][snapshot][sid] = []
                grouped[model_alias][snapshot][sid].append(rec.get("text", ""))

    print(f"loaded {len(files)} raw files across "
          f"{len(grouped)} model(s)")

    # compute BDS per (model, scenario_id)
    out_rows = []
    per_model_bds = {}
    for model_alias, snaps in grouped.items():
        snap_keys = sorted(snaps.keys())
        common_ids = set.intersection(
            *(set(snaps[s].keys()) for s in snap_keys)
        )
        per_model_bds[model_alias] = []
        for sid in sorted(common_ids):
            snap_outputs = {s: snaps[s][sid] for s in snap_keys}
            score = _bds(snap_outputs)
            per_model_bds[model_alias].append(score)
            out_rows.append({
                "model_alias": model_alias,
                "scenario_id": sid,
                "bds": score,
            })

    # write JSON (machine-readable)
    json_path = args.out / "bds_table.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({
            "rows": out_rows,
            "summary": {
                m: {
                    "mean_bds": float(np.mean(v)) if v else None,
                    "median_bds": float(np.median(v)) if v else None,
                    "n_scenarios": len(v),
                }
                for m, v in per_model_bds.items()
            },
        }, f, indent=2)
    print(f"✅ bds_table.json -> {json_path} ({len(out_rows)} rows)")

    # write wide CSV (spreadsheet-friendly)
    csv_path = args.out / "bds_table.csv"
    by_scenario = {}
    for r in out_rows:
        by_scenario.setdefault(r["scenario_id"], {})[
            r["model_alias"]
        ] = r["bds"]
    sorted_models = sorted(per_model_bds)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario_id"] + sorted_models)
        for sid in sorted(by_scenario):
            w.writerow(
                [sid] + [
                    f"{by_scenario[sid].get(m, ''):.4f}"
                    if by_scenario[sid].get(m) is not None else ""
                    for m in sorted_models
                ]
            )
    print(f"✅ bds_table.csv  -> {csv_path}")

    # print summary
    print("\n--- per-model BDS summary ---")
    for m, v in per_model_bds.items():
        if v:
            print(f"   {m:20s}  mean={np.mean(v):.4f}  "
                  f"median={np.median(v):.4f}  "
                  f"n={len(v)}")


if __name__ == "__main__":
    main()
