#!/usr/bin/env python3
"""Read frozen P17 evidence; reproduce statistics without executing upstream code."""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import math
import os
import platform
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from scipy import stats

OVERLAY = Path(__file__).resolve().parents[1]
UP = OVERLAY / "evidence/upstream"
PIPE = OVERLAY / "evidence/pipeline"
LIVE = Path("/home/liuzewen/.research/CALIBRATION_MERGED_FULL_from_data3")
FAMILY = "qf-calibration-fatigue-self-evaluation-frag-3c06d49517"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".p17-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}


def manifest_audit(manifest: Path, base: Path) -> dict[str, Any]:
    payload = load(manifest)
    entries = payload.get("files", payload.get("entries", []))
    if isinstance(entries, dict):
        entries = [{"path": key, **value} for key, value in entries.items()]
    rows = []
    for entry in entries:
        relative = entry["path"]
        target = base / relative
        expected_hash = entry.get("sha256", entry.get("plain_sha256"))
        expected_size = entry.get("size", entry.get("plain_bytes"))
        row = {"path": relative, "expected_sha256": expected_hash,
               "expected_bytes": expected_size}
        if not target.resolve().is_relative_to(base.resolve()):
            row["state"] = "outside-root"
        elif not target.is_file():
            row["state"] = "absent"
        elif not expected_hash:
            row["state"] = "no-hash"
        else:
            row.update(actual_sha256=sha(target), actual_bytes=target.stat().st_size)
            row["state"] = "match" if (
                row["actual_sha256"] == expected_hash.lower()
                and (expected_size is None or expected_size == row["actual_bytes"])
            ) else "mismatch"
        rows.append(row)
    counts = Counter(row["state"] for row in rows)
    return {"manifest": file_record(manifest), "base": str(base), "entries": len(rows),
            "counts": dict(sorted(counts.items())), "rows": rows,
            "all_match": bool(rows) and counts["match"] == len(rows)}


def citations(tex: Path, bib: Path | None = None) -> dict[str, Any]:
    text = re.sub(r"(?m)(?<!\\)%.*$", "", tex.read_text())
    used = {key.strip() for group in re.findall(
        r"\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}", text
    ) for key in group.split(",")}
    declared = [
        name.strip()
        for group in re.findall(r"\\bibliography\s*\{([^}]+)\}", text)
        for name in group.split(",")
        if name.strip()
    ]
    if bib is not None:
        bib_paths = [bib]
    else:
        bib_paths = [
            (tex.parent / name if Path(name).suffix else tex.parent / f"{name}.bib")
            for name in declared
        ]
    missing_bibliographies = [str(path) for path in bib_paths if not path.is_file()]
    available = [path for path in bib_paths if path.is_file()]
    keys = [
        key
        for path in available
        for key in re.findall(
            r"(?mi)^\s*@\w+\s*\{\s*([^,\s]+)\s*,", path.read_text()
        )
    ]
    return {"tex": file_record(tex), "declared": declared,
            "bib": [file_record(path) for path in available],
            "missing_bibliographies": missing_bibliographies,
            "used": sorted(used), "bib_entries": len(keys),
            "missing": sorted(used - set(keys)), "uncited": sorted(set(keys) - used),
            "duplicate_keys": sorted(key for key, n in Counter(keys).items() if n > 1),
            "external_identity_verified": False}


def grid_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    index = {(row["alpha"], row["tau"], row["method"]): row for row in rows}
    if len(index) != len(rows):
        raise ValueError("duplicate calibration grid cell")
    contrasts = []
    for row in rows:
        if row["alpha"] <= 0 or row["method"] == "none":
            continue
        base = index[row["alpha"], row["tau"], "none"]
        contrasts.append({"alpha": row["alpha"], "tau": row["tau"],
                          "method": row["method"],
                          "delta_cv_n5_pct": 100 * (row["CV_N5"] / base["CV_N5"] - 1)})
    methods = {}
    for method in sorted({row["method"] for row in contrasts}):
        values = [row["delta_cv_n5_pct"] for row in contrasts if row["method"] == method]
        methods[method] = {"n": len(values), "mean": float(np.mean(values)),
                           "min": min(values), "max": max(values)}
    values = [row["delta_cv_n5_pct"] for row in contrasts]
    return {"rows": len(rows), "alpha_positive_rows": sum(row["alpha"] > 0 for row in rows),
            "methods": sorted({row["method"] for row in rows}),
            "contrast_count": len(values), "definition": "100*(CV_N5(method)/CV_N5(none)-1), alpha>0; unweighted cells",
            "overall_mean_pct": float(np.mean(values)),
            "condition_range_pct": [min(values), max(values)],
            "method_mean_range_pct": [min(row["mean"] for row in methods.values()),
                                       max(row["mean"] for row in methods.values())],
            "per_method": methods, "contrasts": contrasts,
            "scope": "Reaggregation of stored deterministic-run cells; simulation not rerun."}


def effect(on: list[float], off: list[float], *, equal_var: bool, ddof: int) -> dict[str, float]:
    x, y = np.array(on, dtype=float), np.array(off, dtype=float)
    test = stats.ttest_ind(x, y, equal_var=equal_var)
    if ddof == 0:
        pooled = np.sqrt((x.var(ddof=0) + y.var(ddof=0)) / 2)
    else:
        pooled = np.sqrt(((len(x)-1)*x.var(ddof=1)+(len(y)-1)*y.var(ddof=1))/(len(x)+len(y)-2))
    return {"difference": float(x.mean() - y.mean()), "t": float(test.statistic),
            "p": float(test.pvalue), "d": float((x.mean()-y.mean())/pooled)}


def factorial(values: dict[str, list[float]]) -> dict[str, Any]:
    lengths = {len(values[c]) for c in "ABCD"}
    if len(lengths) != 1 or next(iter(lengths)) < 2:
        raise ValueError("factorial cells must be balanced and nonempty")
    n = next(iter(lengths))
    means = {c: float(np.mean(values[c])) for c in "ABCD"}
    comm = effect(values["B"]+values["D"], values["A"]+values["C"], equal_var=True, ddof=0)
    cal = effect(values["C"]+values["D"], values["A"]+values["B"], equal_var=True, ddof=0)
    interaction = (means["D"]-means["C"])-(means["B"]-means["A"])
    mse = float(np.mean([np.var(values[c], ddof=1) for c in "ABCD"]))
    f_value = n * interaction**2 / 4 / mse
    return {"comm_effect": comm["difference"], "p_comm": comm["p"], "d_comm": comm["d"],
            "cal_effect": cal["difference"], "p_cal": cal["p"], "d_cal": cal["d"],
            "interaction": interaction, "p_interaction": float(stats.f.sf(f_value, 1, 4*n-4)),
            "means": means}


def numeric_diffs(actual: Any, expected: Any, prefix: str = "") -> list[dict[str, Any]]:
    diffs = []
    if isinstance(expected, dict):
        for key, value in expected.items():
            if key not in actual:
                diffs.append({"field": f"{prefix}.{key}", "error": "missing"})
            else:
                diffs.extend(numeric_diffs(actual[key], value, f"{prefix}.{key}"))
    elif isinstance(expected, (int, float)):
        finite_match = (
            math.isfinite(expected)
            and isinstance(actual, (int, float))
            and math.isfinite(actual)
            and abs(actual - expected) <= 1e-9
        )
        nan_match = (
            isinstance(actual, (int, float))
            and math.isnan(expected)
            and math.isnan(actual)
        )
        if not finite_match and not nan_match:
            diffs.append({"field": prefix, "actual": actual, "expected": expected})
    return diffs


def seeds(folder: str, rounds: int) -> dict[str, list[dict[str, Any]]]:
    by = {c: [] for c in "ABCD"}
    for path in sorted((UP / "evidence" / folder).glob("[ABCD]_seed*.json")):
        row = load(path)
        by[row["condition"]].append(row)
    for c, rows in by.items():
        if len(rows) != 30 or {int(v["seed"]) for v in rows} != set(range(30)):
            raise ValueError(f"incomplete/duplicate seeds: {folder}/{c}")
        for row in rows:
            if row["T"] != rounds or len(row["per_round"]) != rounds or row["K"] != 5:
                raise ValueError(f"round/agent count drift: {folder}/{c}")
            if row["comm_on"] != (c in "BD") or row["cal_on"] != (c in "CD"):
                raise ValueError(f"factor assignment drift: {folder}/{c}")
            if [v['round'] for v in row['per_round']] != list(range(rounds)):
                raise ValueError("per-round sequence incomplete")
            for key in ("per_agent_confidence", "per_agent_correctness"):
                if len(row[key]) != 5 or any(len(agent) != rounds for agent in row[key]):
                    raise ValueError(f"incomplete agent traces: {folder}/{c}/{key}")
            if abs(float(np.mean(row["agent_gammas"])) - row["gamma_mean"]) > 1e-9:
                raise ValueError(f"agent gamma mean mismatch: {folder}/{c}")
    return by


def t30_audit(by: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    conditions, metrics = {}, {}
    for metric, source in [("ECE", "ECE"), ("gamma_mean", "gamma_mean"),
                           ("H_final", "H_final"), ("acc", "acc")]:
        metrics[metric] = {c: [float(np.mean([np.mean(agent) for agent in row["per_agent_correctness"]]))
                              if source == "acc" else float(row[source]) for row in by[c]] for c in "ABCD"}
    for c in "ABCD":
        condition = {"n": len(by[c])}
        for key, metric in [("ECE", "ECE"), ("gamma", "gamma_mean"), ("H", "H_final"), ("acc", "acc")]:
            condition[key+"_mean"] = float(np.mean(metrics[metric][c]))
            condition[key+"_std"] = float(np.std(metrics[metric][c], ddof=0))
        conditions[c] = condition
    recomputed = {"total_seeds": 120, "conditions": conditions,
                  "anova": {metric: factorial(values) for metric, values in metrics.items()}}
    expected = load(UP / "evidence/f9_uniform_T30_results/analysis_summary.json")
    csv_path = UP / "evidence/f9_uniform_T30_results/all_results.csv"
    with csv_path.open() as handle:
        csv_rows = list(csv.DictReader(handle))
    indexed = {(row["condition"], int(row["seed"])): row for rows in by.values() for row in rows}
    drift = []
    for row in csv_rows:
        raw = indexed[row["condition"], int(row["seed"])]
        acc = float(np.mean([np.mean(agent) for agent in raw["per_agent_correctness"]]))
        wanted = {key: raw[key] for key in ["ECE", "gamma_mean", "H_final", "elapsed_sec"]}
        wanted.update(gamma_final=raw["per_round"][-1]["gamma"], acc=acc)
        mismatch = [key for key, value in wanted.items() if abs(float(row[key])-value) > 1e-9]
        if mismatch:
            drift.append({"condition": row["condition"], "seed": row["seed"], "fields": mismatch})
    unique = len({(row["condition"], int(row["seed"])) for row in csv_rows})
    return {"recomputed": recomputed, "summary_differences": numeric_diffs(recomputed, expected),
            "csv_rows": len(csv_rows), "csv_unique_seeds": unique, "csv_differences": drift,
            "historical_mismatch": "Upstream REVIEW_ROUND_6 reports prior 24/120 drift; current files tested independently.",
            "method": "Stored seed metrics; Student t main effects, pooled ddof=0 d, interaction F(1,116)."}


def phase(by: dict[str, list[dict[str, Any]]], metric: str, start: int, stop: int) -> dict[str, list[float]]:
    return {c: [float(np.mean([row["per_round"][i][metric] for i in range(start, stop)]))
                for row in by[c]] for c in "ABCD"}


def comm_effect(v: dict[str, list[float]]) -> dict[str, float]:
    return effect(v["B"]+v["D"], v["A"]+v["C"], equal_var=False, ddof=1)


def t50_audit(by: dict[str, list[dict[str, Any]]], t30: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    overall, early_late, comparison = {}, {}, {}
    for metric in ["gamma", "H", "accuracy"]:
        v = phase(by, metric, 49, 50)
        comm = comm_effect(v)
        cal = effect(v["C"]+v["D"], v["A"]+v["B"], equal_var=False, ddof=1)
        overall[metric] = {"comm": comm, "cal": cal,
                           "means": {c: float(np.mean(v[c])) for c in "ABCD"}}
    for metric in ["gamma", "H"]:
        early_late[metric] = {name: comm_effect(phase(by, metric, lo, hi))
                              for name, lo, hi in [("early_R1-5", 0, 5), ("late_R46-50", 45, 50)]}
        comparison[metric] = {name: comm_effect(phase(rows, metric, 25, 30))
                              for name, rows in [("T=30", t30), ("T=50", by)]}
    convergence = {}
    for c in "ABCD":
        crossing = [next(i+1 for i, r in enumerate(row["per_round"])
                         if r["gamma"] >= 0.9*row["per_round"][-1]["gamma"])
                    for row in by[c] if row["per_round"][-1]["gamma"] > 0]
        convergence[c] = float(np.mean(crossing))
    expected = load(UP / "evidence/f9_T50_analysis/analysis_summary.json")
    subset = {"overall": {k: v for k, v in expected["overall"].items() if k != "ECE"},
              "early_vs_late": expected["early_vs_late"], "t30_vs_t50": expected["t30_vs_t50"],
              "mechanism": {"convergence_speed": expected["mechanism"]["convergence_speed"]}}
    recomputed = {"overall": overall, "early_vs_late": early_late, "t30_vs_t50": comparison,
                  "mechanism": {"convergence_speed": convergence}}
    return {"total_seeds": sum(len(rows) for rows in by.values()), "recomputed": recomputed,
            "summary_differences": numeric_diffs(recomputed, subset),
            "per_round_records": sum(len(row["per_round"]) for rows in by.values() for row in rows),
            "ece_round_fields_present": sum("ECE" in r for rows in by.values() for row in rows for r in row["per_round"]),
            "stored_ece_nonfinite_means": sum(not math.isfinite(v) for v in expected["overall"]["ECE"]["means"].values()),
            "ece_state": "unavailable: per-round ECE absent; cannot interpret stored NaN as zero or null effect",
            "strengthening_threshold_d": 0.30,
            "late_gamma_exceeds_threshold": early_late["gamma"]["late_R46-50"]["d"] > 0.30,
            "method": "Final-round and per-seed phase means; Welch t, pooled sample-SD Cohen d. Nonsignificance does not establish equivalence."}


def real_pilot() -> dict[str, Any]:
    rows = [json.loads(line) for line in (UP / "evidence/real_pilot_qwen2/per_seed.jsonl").read_text().splitlines() if line.strip()]
    results = {}
    for condition in sorted({row["condition"] for row in rows}):
        selected = [row for row in rows if row["condition"] == condition]
        groups = [[row for row in selected if row["question_id"] == q]
                  for q in sorted({row["question_id"] for row in selected})]
        if len(groups) != 20 or any(len(group) != 5 for group in groups):
            raise ValueError("real pilot incomplete")
        x = [row["confidence"] for row in selected]
        y = [float(row["correct"]) for row in selected]
        cv = [float(np.std([r["confidence"] for r in group], ddof=0)/np.mean([r["confidence"] for r in group])) for group in groups]
        question_x = [np.mean([r["confidence"] for r in group]) for group in groups]
        question_y = [np.mean([r["correct"] for r in group]) for group in groups]
        results[condition] = {"rows": len(selected), "questions": len(groups),
                              "mean_question_cv": float(np.mean(cv)),
                              "individual_pearson": float(stats.pearsonr(x, y).statistic),
                              "question_mean_pearson": float(stats.pearsonr(question_x, question_y).statistic)}
    return {"rows": len(rows), "results": results,
            "boundary": "A local temperature probe; no GPT-4o reproduction or generalization established."}


def trace_ece(confidence: list[float], correct: list[int], bins: int = 10) -> float:
    """Match the archived driver's rank-sorted, equal-count ECE convention."""
    if len(confidence) != len(correct) or len(confidence) < bins:
        raise ValueError("ECE requires aligned traces with at least one item per bin")
    if any(not math.isfinite(c) or not 0 <= c <= 1 for c in confidence):
        raise ValueError("invalid confidence")
    if any(c not in (0, 1) for c in correct):
        raise ValueError("invalid correctness")
    pairs = sorted(zip(confidence, correct), key=lambda pair: pair[0])
    width = len(pairs) // bins
    result = 0.0
    for index in range(bins):
        group = pairs[index * width:(index + 1) * width] if index < bins - 1 else pairs[index * width:]
        result += len(group) / len(pairs) * abs(
            sum(c for c, _ in group) / len(group) - sum(y for _, y in group) / len(group)
        )
    return round(result, 4)


def ece_recovery(by: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rows, differences = [], []
    for condition in "ABCD":
        for row in sorted(by[condition], key=lambda item: item["seed"]):
            confidence = [c for agent in row["per_agent_confidence"] for c in agent]
            correct = [c for agent in row["per_agent_correctness"] for c in agent]
            computed = trace_ece(confidence, correct)
            item = {"condition": condition, "seed": row["seed"],
                    "pairs": len(confidence), "computed": computed, "stored": row["ECE"]}
            rows.append(item)
            if not math.isfinite(row["ECE"]) or abs(computed - row["ECE"]) > 1e-9:
                differences.append(item)
    groups = {c: [row["computed"] for row in rows if row["condition"] == c] for c in "ABCD"}
    return {
        "definition": "Rank-sort confidence/correctness pairs in agent-major order; 10 equal-count bins, remainder in last bin; round per-seed ECE to 4 decimals. Ties preserve input order, as in archived drivers.",
        "observations": sum(row["pairs"] for row in rows),
        "seed_rows": len(rows), "stored_metric_differences": differences,
        "conditions": {c: {"mean": float(np.mean(groups[c])),
                           "sd": float(np.std(groups[c], ddof=1))} for c in "ABCD"},
        "range": [min(row["computed"] for row in rows), max(row["computed"] for row in rows)],
        "comm": comm_effect(groups),
        "cal": effect(groups["C"] + groups["D"], groups["A"] + groups["B"], equal_var=False, ddof=1),
        "rows": rows,
        "scope": "New retrospective reaggregation of archived pairs, not a new API experiment or a preregistered ECE test. Neither nonsignificance nor repaired NaN establishes equivalence. Not equal-width ECE; tied-confidence bins have convention dependence.",
    }


def self_test() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        data = root / "data"
        data.write_bytes(b"frozen")
        manifest = root / "manifest.json"
        write(manifest, {"files": [{"path": "data", "sha256": sha(data), "size": 6}]})
        assert manifest_audit(manifest, root)["all_match"]
        data.write_bytes(b"tamper")
        assert manifest_audit(manifest, root)["counts"] == {"mismatch": 1}
        data.unlink()
        assert manifest_audit(manifest, root)["counts"] == {"absent": 1}
        write(manifest, {"files": [{"path": "../escape", "sha256": "0"*64}]})
        assert manifest_audit(manifest, root)["counts"] == {"outside-root": 1}
        tex, bib = root / "main.tex", root / "refs.bib"
        tex.write_text(r"\citep{present,missing}")
        bib.write_text("@article{present, title={x}}")
        assert citations(tex, bib)["missing"] == ["missing"]
        added = root / "added.bib"
        added.write_text("@misc{missing, title={y}}")
        tex.write_text(r"\citep{present,missing}\bibliography{refs,added}")
        multi = citations(tex)
        assert multi["missing"] == [] and len(multi["bib"]) == 2
        added.unlink()
        absent = citations(tex)
        assert absent["missing"] == ["missing"]
        assert absent["missing_bibliographies"] == [str(added)]
    assert trace_ece([0.5] * 10, [0, 1] * 5) == 0.5
    assert trace_ece([0.5] * 20, [0, 1] * 10) == 0
    for confidence, correct in [([0.5] * 10, [0] * 9), ([1.5] * 10, [0] * 10)]:
        try:
            trace_ece(confidence, correct)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid ECE inputs accepted")
    grid = grid_audit([{"alpha": 1, "tau": 1, "method": "none", "CV_N5": 2},
                       {"alpha": 1, "tau": 1, "method": "a", "CV_N5": 3},
                       {"alpha": 1, "tau": 1, "method": "b", "CV_N5": 1}])
    assert grid["condition_range_pct"] == [-50, 50] and grid["overall_mean_pct"] == 0
    assert numeric_diffs({"x": 1}, {"x": 2})
    print("P17 self-test: tamper, missing file, path escape, missing citation, CV range and numeric drift detected")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    snapshot = load(OVERLAY / "evidence/snapshot.json")
    for row in snapshot["files"]:
        path = OVERLAY / row["path"]
        if sha(path) != row["sha256"] or path.stat().st_size != row["bytes"]:
            raise ValueError(f"frozen input integrity failed: {row['path']}")
    canonical = UP / "main.tex"
    text = canonical.read_text()
    variants = []
    paths = [canonical, *sorted(UP.glob("main.tex.bak*")), UP/"arxiv_clean/main.tex",
             UP/"paper/main.tex", PIPE/"main.tex", PIPE/"paper/main.tex", PIPE/"arxiv_clean/main.tex"]
    for path in paths:
        content = path.read_text()
        variants.append({**file_record(path), "lines": len(content.splitlines()),
                         "four_findings": "four findings" in content.lower(),
                         "three_findings": "three findings" in content.lower(),
                         "t50_markers": content.count("T{=}50")})
    preprint = (UP/"arxiv_clean/main.tex").read_text()
    opcodes = difflib.SequenceMatcher(None, text.splitlines(), preprint.splitlines()).get_opcodes()
    reconciliation = {"retained_files": len(variants),
                      "distinct_hashes": len({row["sha256"] for row in variants}),
                      "rows": variants, "diff_opcode_count": len(opcodes),
                      "changed_line_slots": sum(max(j-i, l-k) for tag, i, j, k, l in opcodes if tag != "equal"),
                      "preprint_equals_backup": sha(UP/"arxiv_clean/main.tex") == sha(UP/"main.tex.bak_preprint"),
                      "canonical_scope_note": "canonical, merged version" in text,
                      "canonical_author_anonymous": bool(re.search(r"\\author\s*\{\s*(?:\\name\s+)?Anonymous", text)),
                      "decision": "Retain full source as audit baseline; preprint is an older three-finding version, not a completed merge."}
    manifests = {
        "evidence": manifest_audit(UP/"evidence/evidence_manifest.json", LIVE/"evidence"),
        "outer": manifest_audit(UP/"evidence_manifest.json", LIVE),
        "arxiv": manifest_audit(UP/"arxiv_clean/evidence_manifest.json", LIVE/"arxiv_clean"),
        "arxiv_generated": manifest_audit(UP/"arxiv_clean/evidence_manifest_generated.json", LIVE/"arxiv_clean"),
    }
    archive = load(UP/"evidence/archived_joint_2x2_30seed_20260811.json")
    gamma = {c: archive["conditions"][c]["final_gamma_mean_per_rep"] for c in "ABCD"}
    archive_result = {"ac_identical": gamma["A"] == gamma["C"], "ad_identical": gamma["A"] == gamma["D"],
                      "ab_identical": gamma["A"] == gamma["B"], "A_values": gamma["A"],
                      "state": "excluded: upstream explicitly marks corrupt; equal A/C/D arrays confirmed"}
    receipts = load(PIPE/"evidence/CARRIER_RECEIPTS.json")
    summary = load(PIPE/"evidence/finding1_rerun_qwen32b/finding1_summary.json")
    bound_to_reference = [row for row in receipts if str(row.get("value")) == "90.8"
                          and row.get("over") == "decomposition.pure_T.paper_pct"]
    computed_pct = 100 * (summary["conditions"]["C1b"]["mean"]-summary["conditions"]["C1"]["mean"]) / (summary["conditions"]["C2"]["mean"]-summary["conditions"]["C1"]["mean"])
    carrier = {"receipt_count": len(receipts), "mechanical_verdicts": dict(Counter(r.get("_verdict", "absent") for r in receipts)),
               "reference_bound_90_8_receipts": len(bound_to_reference),
               "examples": bound_to_reference[:2], "reference_paper_pct": summary["decomposition"]["pure_T"]["paper_pct"],
               "qwen_temporal_share_pct_from_rounded_condition_means": computed_pct,
               "interpretation": "paper_pct is a comparison reference, not a Qwen measured temporal share or archived GPT-4o raw trace.",
               "finding1_raw_carrier_state": "missing per upstream finding1_data_GAP and ledger; search scoped to delivered evidence",
               "finding2_raw_carrier_state": "NOT_ARCHIVED in upstream C07/C08/C10; 1.06/42%/35-37% remain blocked"}
    t30 = seeds("f9_uniform_T30_results", 30)
    t50 = seeds("f9_t50_results", 50)
    recovered = {"schema": "q-one-p17-ece-recovery-v1",
                 "inputs": file_record(OVERLAY / "evidence/snapshot.json"),
                 "definition_inputs": file_record(OVERLAY / "evidence/recovery/ece-definition-inputs.json"),
                 "runner": file_record(Path(__file__).resolve()),
                 "T30": ece_recovery(t30), "T50": ece_recovery(t50)}
    audit = {"schema": "q-one-p17-calibration-audit-v1", "generated_at": snapshot["captured_at"],
             "family_id": FAMILY, "marker": "agent-proposed, not human publication approval",
             "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "platform": platform.platform()},
             "command": "python research/pilot-calibration-fatigue/tools/audit_p17.py",
             "runner": file_record(Path(__file__).resolve()), "snapshot": file_record(OVERLAY/"evidence/snapshot.json"),
             "canonical": file_record(canonical), "variants": reconciliation, "manifests": manifests,
             "citations": {"canonical": citations(canonical),
                           "preprint": citations(UP/"arxiv_clean/main.tex")},
             "grid": grid_audit(load(UP/"evidence/canonical_results_v5.json")),
             "corrupt_archive": archive_result, "carrier_semantics": carrier,
             "t30": t30_audit(t30), "t50": t50_audit(t50, t30),
             "ece_recovery": recovered, "real_pilot": real_pilot(),
             "decision": {"disposition": "blocked", "status": "blocked", "independent_package_created": False,
                          "uploaded": False, "scientific_ready": False,
                          "reason": "Missing headline raw traces; corrupt predecessor; stale manifests; citation and method-review gaps."}}
    source = {"schema": "q-one-p17-source-record-v1", "canonical_origin": str(LIVE/"main.tex"),
              "canonical_sha256": sha(canonical), "byte_identical": sha(canonical) == sha(LIVE/"main.tex"),
              "snapshot_sha256": sha(OVERLAY/"evidence/snapshot.json"), "frozen_files": len(snapshot["files"]),
              "scope_note_present": reconciliation["canonical_scope_note"], "author_anonymous": reconciliation["canonical_author_anonymous"],
              "authority": "audit baseline selection only; author/license/upload unchanged"}
    grid = audit["grid"]
    values = {"canonical_sha256": sha(canonical), "snapshot_files": len(snapshot["files"]),
              "source_byte_identical": int(source["byte_identical"]),
              "preprint_equals_backup": int(reconciliation["preprint_equals_backup"]),
              "variant_files": len(variants), "variant_hashes": reconciliation["distinct_hashes"],
              "evidence_manifest_entries": manifests["evidence"]["entries"],
              "evidence_manifest_match": manifests["evidence"]["counts"].get("match", 0),
              "outer_manifest_mismatch": manifests["outer"]["counts"].get("mismatch", 0),
              "outer_manifest_absent": manifests["outer"]["counts"].get("absent", 0),
              "arxiv_manifest_mismatch": manifests["arxiv"]["counts"].get("mismatch", 0),
              "generated_manifest_mismatch": manifests["arxiv_generated"]["counts"].get("mismatch", 0),
              "grid_rows": grid["rows"], "grid_contrasts": grid["contrast_count"], "grid_mean_delta_pct": grid["overall_mean_pct"],
              "grid_cell_min_pct": grid["condition_range_pct"][0], "grid_cell_max_pct": grid["condition_range_pct"][1],
              "acd_equal": int(gamma["A"] == gamma["C"] == gamma["D"]),
              "missing_citations": len(audit["citations"]["canonical"]["missing"]),
              "canonical_cited_keys": len(audit["citations"]["canonical"]["used"]),
              "missing_bibliographies": len(audit["citations"]["canonical"]["missing_bibliographies"]),
              "citation_identity_sources": len(load(OVERLAY / "evidence/citation-identity.json")["sources"]),
              "t50_ece_recovered_seeds": recovered["T50"]["seed_rows"],
              "t50_ece_observations": recovered["T50"]["observations"],
              "t50_ece_stored_differences": len(recovered["T50"]["stored_metric_differences"]),
              "t50_ece_comm_p": recovered["T50"]["comm"]["p"],
              "t50_ece_cal_p": recovered["T50"]["cal"]["p"],
              "t30_ece_stored_differences": len(recovered["T30"]["stored_metric_differences"]),
              "t30_seeds": 120, "t50_seeds": 120,
              "t30_csv_differences": len(audit["t30"]["csv_differences"]),
              "t30_summary_differences": len(audit["t30"]["summary_differences"]),
              "t50_summary_differences": len(audit["t50"]["summary_differences"]),
              "t50_late_gamma_d": audit["t50"]["recomputed"]["early_vs_late"]["gamma"]["late_R46-50"]["d"],
              "t50_late_gamma_p": audit["t50"]["recomputed"]["early_vs_late"]["gamma"]["late_R46-50"]["p"],
              "t50_ece_round_fields": audit["t50"]["ece_round_fields_present"],
              "reference_bound_90_8_receipts": len(bound_to_reference), "qwen_temporal_share_pct": computed_pct,
              "real_pilot_rows": audit["real_pilot"]["rows"],
              "revision_cleanroom_pages": load(OVERLAY / "reports/cleanroom-internal-20261028/receipt.json")["pdf"]["pages"],
              "revision_cleanroom_deterministic": int(load(OVERLAY / "reports/cleanroom-internal-20261028/receipt.json")["pdf"]["deterministic"]),
              "independent_package_created": 0, "uploaded": 0}
    for c, result in audit["real_pilot"]["results"].items():
        values[c+"_cv"] = result["mean_question_cv"]
        values[c+"_coupling"] = result["individual_pearson"]
    for name, payload in [("audit", audit), ("source_record", source), ("variant-reconciliation", reconciliation), ("claim-values", values),
                          ("ece-recovery", recovered)]:
        write(OVERLAY/"evidence"/(name+".json"), payload)
    print(json.dumps({"source": source, "values": values, "manifests": {k: v["counts"] for k, v in manifests.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
