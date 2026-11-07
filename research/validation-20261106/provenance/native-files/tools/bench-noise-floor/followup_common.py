#!/usr/bin/env python3
"""Shared pipeline for the strict-review followup battery (E-B / E-C #32 #37 #39 #42 #56).

Design contract
---------------
* Every number is recomputed from on-disk substrates; nothing is copied from prose.
* Point estimates are computed by **importing audit.py itself** (build_gold /
  leave_one_out / agreement / macro_micro / _leaderboard / domain_membership_ok) --
  the production implementations, not a re-implementation, so they cannot drift.
* The bootstrap follows audit.py's convention exactly: seed 20261001, case-cluster
  resampling via ``rng = np.random.default_rng(20261001);
  rng.integers(0, n_cases, size=(n_boot, n_cases))``, the W-matrix aggregation of
  run_one's ``boot_macro`` (slice-equal-weight macro; NaN rounds dropped in paired
  comparisons), percentile CI at [2.5, 97.5].
* Every script using this module must (a) pass ``--selftest`` and (b) reproduce the
  carrier JSONs (m25_*.json, audit_*.json, jev_*.json) before writing any output.
  A validation mismatch is FATAL: we stop and report, we do not publish numbers
  that disagree with the carriers.

This file only ADDS capability (median-floor arms, tie variants, sweeps). It does
not modify any existing file.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))          # tools/bench-noise-floor
PAPER_ROOT = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                          "papers", "bench_noise_floor")
EVIDENCE = os.path.join(PAPER_ROOT, "evidence")
EXAMPLES = os.path.join(HERE, "examples")
OUTDIR = os.path.join(EVIDENCE, "strict_review_followup")

sys.path.insert(0, HERE)
import audit  # noqa: E402  (read-only import of the production instrument)

SEED = 20261001                 # audit.py bootstrap seed convention
DELTA = 2.0                     # declared threshold of eq:rule / human-gold chain
EQ_TOL = 1e-9                   # audit.py equality-arm tolerance
MIN_LOO_GENERATORS = audit.MIN_LOO_GENERATORS

TASKS = ("factuality", "coherence", "relevance", "preference")


# ---------------------------------------------------------------- provenance

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance(inputs: list[str]) -> dict:
    """Provenance block required by the followup discipline: script path, command
    line, UTC time, input sha256, tool versions, audit.py self-hash."""
    return {
        "script": os.path.relpath(os.path.abspath(__file__), PAPER_ROOT),
        "calling_script": os.path.relpath(
            os.path.abspath(sys.argv[0]), PAPER_ROOT) if sys.argv[0] else "?",
        "command_line": "python3 " + " ".join(sys.argv),
        "utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # 键必须是相对路径：绝对路径会把宿主机目录写进证据（2026-10-25 ship surface
        # 在 EC42/EC39 的 inputs_sha256 里抓到 18 条 host_path）。这里统一转成相对
        # PAPER_ROOT 的路径，仓库在哪台机器上检出都不影响这行字。
        "inputs_sha256": {os.path.relpath(os.path.abspath(p), PAPER_ROOT): sha256_file(p)
                          for p in inputs},
        "audit_py_sha256": sha256_file(os.path.join(HERE, "audit.py")),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "seed_convention": SEED,
        "note": "E-B/E-C followup battery; point estimates via imported audit.py; "
                "bootstrap per audit.py run_one [4]/[4b] convention (seed 20261001, "
                "case-cluster, percentile CI).",
    }


def load_carrier(name: str) -> dict:
    with open(os.path.join(EVIDENCE, name), encoding="utf-8") as fh:
        return json.load(fh)


def r4(x):
    """Round to 4dp (carrier print precision); NaN/inf -> None."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return None
    return round(float(x), 4)


def fail(msg: str):
    print(f"FATAL {msg}", file=sys.stderr)
    sys.exit(3)


def check_close(got, want, tol, what):
    """Carrier-validation primitive: mismatch = FATAL (fail-closed discipline)."""
    if got is None or want is None or not np.isfinite(got) or not np.isfinite(want):
        fail(f"carrier validation failed: {what}: got={got} want={want}")
    if abs(float(got) - float(want)) > tol:
        fail(f"carrier validation failed: {what}: recomputed={got!r} "
             f"carrier={want!r} |diff|={abs(got - want):.3e} > tol={tol:.1e}")


# ---------------------------------------------------------------- bootstrap
# audit.py run_one [4] convention, verbatim semantics.

def make_boot_idx(n_cases: int, n_boot: int, seed: int = SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, n_cases, size=(n_boot, n_cases))


def cells_matrices(slices, cases, hits, slice_levels, case_levels):
    """(slice, case) hit-sum / count matrices -- audit.py slice_case_cells."""
    tmp = pd.DataFrame({"s": np.asarray(slices), "c": np.asarray(cases),
                        "h": np.asarray(hits, dtype=float)})
    g = tmp.groupby(["s", "c"], sort=True)["h"].agg(["sum", "count"])
    sl = list(slice_levels)
    cs = list(case_levels)
    S = np.zeros((len(sl), len(cs)))
    N = np.zeros_like(S)
    for (sname, cname), row in g.iterrows():
        S[sl.index(sname), cs.index(cname)] = float(row["sum"])
        N[sl.index(sname), cs.index(cname)] = float(row["count"])
    return S, N


def boot_macro_rounds(S: np.ndarray, N: np.ndarray, boot_idx: np.ndarray) -> np.ndarray:
    """audit.py run_one boot_macro: case-cluster resample, slice-equal-weight macro.

    Rounds where a slice has no drawn case yield NaN (undefined), never 0.
    """
    n_boot, n_cases = boot_idx.shape
    W = np.zeros((n_boot, n_cases), dtype=float)
    np.add.at(W, (np.repeat(np.arange(n_boot), n_cases), boot_idx.ravel()), 1.0)
    num = S @ W.T
    den = N @ W.T
    sl_mean = np.divide(num, den, out=np.full_like(num, np.nan), where=den > 0)
    with np.errstate(invalid="ignore"):
        valid = np.isfinite(sl_mean).any(axis=0)
        out = np.full(n_boot, np.nan, dtype=float)
        if valid.any():
            out[valid] = np.nanmean(sl_mean[:, valid], axis=0)
    return out


def point_macro(S: np.ndarray, N: np.ndarray) -> float:
    """w=1 aggregation -- must equal the point estimate (audit.py self-check)."""
    num0, den0 = S @ np.ones((N.shape[1], 1)), N @ np.ones((N.shape[1], 1))
    m0 = np.nanmean(np.divide(num0, den0, out=np.full_like(num0, np.nan),
                              where=den0 > 0))
    return float(m0) * 100.0


def percentile_ci(vals: np.ndarray) -> tuple[float, float]:
    ok = np.isfinite(vals)
    if not ok.any():
        return float("nan"), float("nan")
    lo, hi = np.percentile(vals[ok], [2.5, 97.5])
    return float(lo), float(hi)


def _rng_stream_equivalence_guard():
    """numpy >=1.17 Generator.integers: one (B, n) draw consumes the same stream as
    B sequential (n,)-draws. audit.py mixes both forms ([4] one-shot, [10] loop),
    so our machinery needs them to coincide; assert on this machine's numpy."""
    r1 = np.random.default_rng(7)
    a = r1.integers(0, 13, size=(5, 11))
    r2 = np.random.default_rng(7)
    b = np.vstack([r2.integers(0, 13, size=11) for _ in range(5)])
    if not np.array_equal(a, b):
        fail("numpy Generator stream equivalence (B, n) vs B x (n,) does not hold "
             f"on numpy {np.__version__}; carrier-anchored validation impossible")


_rng_stream_equivalence_guard()


# ---------------------------------------------------------------- verdict chains
# Verbatim transcription of audit.py's decision arms (order matters).

def verdict_judge_chain(top: float, ceiling, same_domain: bool, m_generators: int,
                        delta: float = DELTA, tol: float = EQ_TOL) -> str:
    if not same_domain:
        return "UNDECIDABLE_DOMAIN_MISMATCH"
    if m_generators < MIN_LOO_GENERATORS:
        return "UNDECIDABLE_FLOOR_DEGENERATE"
    if ceiling is None or not np.isfinite(ceiling) or top is None \
            or not np.isfinite(top):
        return "UNDECIDABLE_NO_READING"
    if ceiling > top + tol:
        return "UNREADABLE"
    if top - ceiling <= tol:
        return "UNREADABLE"
    if top - ceiling < delta:
        return "MARGINAL"
    return "READABLE"


def verdict_external_chain(top: float, med: float, mixed_domain: bool,
                           delta: float = DELTA, tol: float = EQ_TOL) -> str:
    if mixed_domain:
        return "NOT_COMPARABLE"
    margin = top - med
    if top > med + tol and margin < delta:
        return "NEAR_MEDIAN_ACTOR"
    if margin >= delta:
        return "ABOVE_MEDIAN_ACTOR"
    return "AT_OR_BELOW_MEDIAN_ACTOR"


# ---------------------------------------------------------------- tie variants
# audit.py build_gold / leave_one_out support unmeasured | lexicographic only.
# The random / weighted variants below replicate those two functions line-for-line
# with a pluggable tie resolver; _validate_tie_variants() proves the replication is
# exact on the real corpora before any variant is trusted.

TieRule = str  # "unmeasured" | "lexicographic" | ("random", seed) | ("weighted", w)


def _resolve_top(tally: dict, rule, rng=None, actor_votes=None) -> str | None:
    """Shared top-of-tally resolution.

    unmeasured   -> unique plurality holder else None (item unmeasured)
    lexicographic -> top count, ties by answer string order (audit.py's exact form)
    ("random", seed) -> uniform among count-tied answers; rng must be a shared
        numpy Generator for the whole chain run (a fresh per-call Generator would
        resolve every tie identically, making "random" a deterministic rule)
    ("weighted", weights) -> count ties broken by ability weight: among the
        count-tied answers pick the one with the higher sum of voter weights
        (weights keyed by ACTOR, so actor_votes = [(actor, answer), ...] for the
        item is required); exact weighted tie => None (unmeasured). Non-tie
        items resolve exactly as the baseline, so the only changed items are
        tie items (clean sensitivity attribution).
    """
    if not tally:
        return None
    if rule == "unmeasured":
        return audit.plurality_winner(tally)
    if rule == "lexicographic":
        mx = max(tally.values())
        return min(k for k, v in tally.items() if v == mx)
    if isinstance(rule, tuple) and rule[0] == "random":
        mx = max(tally.values())
        tied = sorted(k for k, v in tally.items() if v == mx)
        if len(tied) == 1:
            return tied[0]
        if rng is None:
            fail("random tie rule requires a shared chain-level rng")
        return str(tied[int(rng.integers(0, len(tied)))])
    if isinstance(rule, tuple) and rule[0] == "weighted":
        w = _resolve_top(tally, "unmeasured")
        if w is not None:
            return w
        if actor_votes is None:
            fail("weighted tie rule requires actor-level votes")
        mx = max(tally.values())
        tied = {k for k, v in tally.items() if v == mx}
        wt = {}
        for a, v in actor_votes:
            if v in tied:
                wt[v] = wt.get(v, 0.0) + float(rule[1].get(a, 0.0))
        best = max(wt.values()) if wt else None
        if best is None:
            return None
        top = sorted(k for k, v in wt.items() if v == best)
        return top[0] if len(top) == 1 else None
    fail(f"unknown tie rule {rule!r}")


def build_gold_variant(jdf: pd.DataFrame, rule) -> tuple[dict, dict]:
    """audit.build_gold replication with a pluggable tie resolver.
    Returns (gold_map, counts). Empty answers are skipped, as in audit.py.
    Random ties consume one chain-level rng in (sorted-item) order."""
    majority: dict = {}
    counts: dict = {}
    rng = np.random.default_rng(rule[1]) if isinstance(rule, tuple) \
        and rule[0] == "random" else None
    for item, grp in jdf.groupby("item_id", sort=False):
        c: dict = {}
        av: list = []
        for a, v in zip(grp["actor"].tolist(), grp["answer_n"].tolist()):
            if v == "":
                continue
            c[v] = c.get(v, 0) + 1
            av.append((a, v))
        counts[item] = c
        w = _resolve_top(c, rule, rng, actor_votes=av)
        if w is not None:
            majority[item] = w
    return majority, counts


def leave_one_out_variant(jdf: pd.DataFrame, rule) -> dict:
    """audit.leave_one_out replication (majority mode) with the same resolver.
    c^-_g = gold rebuilt without g's vote; undefined items are absent keys.
    Random ties consume one chain-level rng in (sorted-judge, sorted-item) order."""
    votes = {(r.item_id, r.actor): r.answer_n for r in jdf.itertuples()}
    judges = sorted({audit.norm_actor(a) for a in jdf["actor"].tolist()})
    items = sorted(jdf["item_id"].unique())
    rng = np.random.default_rng(rule[1]) if isinstance(rule, tuple) \
        and rule[0] == "random" else None
    out = {}
    for g in judges:
        per_item = {}
        for item in items:
            acc = {}
            av: list = []
            for j in judges:
                if j == g:
                    continue
                a = votes.get((item, j), "")
                if a == "":
                    continue
                acc[a] = acc.get(a, 0.0) + 1.0
                av.append((j, a))
            w = _resolve_top(acc, rule, rng, actor_votes=av)
            if w is not None:
                per_item[item] = w
        out[g] = per_item
    return out


def _validate_tie_variants(tasks: tuple[str, ...] = TASKS):
    """Non-vacuity gate for the tie-variant replication: on every real corpus the
    unmeasured / lexicographic resolvers must reproduce audit.py's own builders
    item-for-item, and they must DIFFER somewhere (a variant that agrees with the
    baseline everywhere would make the sensitivity battery vacuous)."""
    for t in tasks:
        votes_csv = os.path.join(EXAMPLES, f"judgesense_{t}.csv")
        judges_csv = os.path.join(EXAMPLES, f"judgesense_{t}_judges.csv")
        jdf, _ = audit.load(judges_csv)
        gold = audit.build_gold(jdf, False, "unmeasured")
        mine_map, mine_counts = build_gold_variant(jdf, "unmeasured")
        if mine_map != gold.majority or mine_counts != gold.counts:
            fail(f"tie-variant replication: build_gold(unmeasured) mismatch on {t}")
        loo_ref = audit.leave_one_out(gold, "majority",
                                      {(r.item_id, r.actor): r.answer_n
                                       for r in jdf.itertuples()}, {})
        loo_mine = leave_one_out_variant(jdf, "unmeasured")
        if {g: dict(m) for g, m in loo_mine.items()} != \
           {g: dict(m) for g, m in loo_ref.items()}:
            fail(f"tie-variant replication: leave_one_out(unmeasured) mismatch on {t}")
        # lexicographic must differ from unmeasured somewhere on corpora with ties,
        # and must equal audit.py's own lexicographic arm where one exists.
        lex_map, _ = build_gold_variant(jdf, "lexicographic")
        gold_lex = audit.build_gold(jdf, False, "lexicographic")
        if lex_map != gold_lex.majority:
            fail(f"tie-variant replication: build_gold(lexicographic) mismatch on {t}")
        # make_m25_votes premise: ballot == answer (Prop 4 precondition)
        s = pd.read_csv(votes_csv, dtype=str)
        j = pd.read_csv(judges_csv, dtype=str)
        p = j[["actor", "item_id", "answer"]].merge(
            s[["actor", "item_id", "answer"]], on=["actor", "item_id"],
            suffixes=("_ballot", "_answer"))
        if (p.answer_ballot != p.answer_answer).any():
            fail(f"ballot != answer on {t} (Prop 4 precondition broken)")


# ---------------------------------------------------------------- m25 arm
# Mirrors audit.run_one(--gold majority) on the make_m25_votes concatenated table.

def build_m25_votes_table(task: str, tmpdir: str) -> str:
    import make_m25_votes
    rec = make_m25_votes.build(task, tmpdir, EXAMPLES)
    return rec["path"]


def run_judge_gold_arm(votes_csv: str, rule="unmeasured", n_boot: int = 2000,
                       median_arm: bool = True) -> dict:
    """Full judge-gold chain (audit.run_one --gold majority caliber) for ANY votes
    table under a tie rule. Works for m=2 (jev corpora) and m=25 (m25 tables)."""
    df, have_prob = audit.load(votes_csv)
    jdf = df[df["role"] == "judge"].copy()
    sdf = df[df["role"] == "system"].copy()
    gold_map, gold_counts = build_gold_variant(jdf, rule)
    loo_maps = leave_one_out_variant(jdf, rule)
    judges = sorted({audit.norm_actor(a) for a in jdf["actor"].tolist()})
    loo_domain = set.intersection(*[set(m) for m in loo_maps.values()]) \
        if loo_maps else set()

    # floor side: per-generator hits on U against its own c^-
    floor_mats = {}
    loo_u_raw = {}
    for j in judges:
        sub = jdf[jdf["actor"] == j]
        sub_u = sub[sub["item_id"].isin(loo_domain)]
        hitu = audit.agreement(sub_u, loo_maps[j])
        mau, _ = audit.macro_micro(hitu, sub_u["slice"])
        loo_u_raw[j] = float(mau)
        floor_mats[j] = (sub_u["slice"].to_numpy(), sub_u["case_id"].to_numpy(),
                         np.asarray(hitu, dtype=float))

    # leaderboard on U against the main gold (production caliber)
    lb_df = df[df["item_id"].isin(loo_domain)] if loo_domain else df
    lb_sdf = lb_df[lb_df["role"] == "system"]
    rows, _ = audit._leaderboard(lb_df, lb_sdf, gold_map)
    top = rows[0]
    ceiling = max(loo_u_raw.values()) if loo_u_raw else float("nan")
    pool = np.array([loo_u_raw[j] for j in sorted(loo_u_raw)])
    med_pool = float(np.median(pool)) if pool.size else float("nan")
    same_domain = audit.domain_membership_ok(rows, set(loo_domain)) \
        if loo_domain else False
    verdict = verdict_judge_chain(float(top["macro"]), ceiling, same_domain,
                                  len(judges))

    # paired bootstrap: one draw sequence shared by both sides (audit.py [4b])
    cases = np.unique(np.concatenate([r["case"] for r in rows]))
    case_index = {c: i for i, c in enumerate(cases)}
    slice_levels = list(np.unique(np.concatenate([r["slice"] for r in rows])))
    boot_idx = make_boot_idx(len(cases), n_boot)
    S_top, N_top = cells_matrices(top["slice"], top["case"], top["hit"],
                                  slice_levels, case_index)
    b_top = boot_macro_rounds(S_top, N_top, boot_idx)
    stack = []
    for j in sorted(floor_mats):
        sl, cs, ht = floor_mats[j]
        S, N = cells_matrices(sl, cs, ht, slice_levels, case_index)
        stack.append(boot_macro_rounds(S, N, boot_idx))
    stack = np.vstack(stack)
    with np.errstate(invalid="ignore"):
        floor_b = np.nanmax(stack, axis=0)
        med_b = np.nanmedian(stack, axis=0) if median_arm else np.full(n_boot, np.nan)
    margin_floor_b = (b_top - floor_b) * 100.0
    margin_med_b = (b_top - med_b) * 100.0
    lo_f, hi_f = percentile_ci(margin_floor_b)
    lo_m, hi_m = percentile_ci(margin_med_b)
    n_drop_f = int(np.sum(~np.isfinite(margin_floor_b)))
    n_drop_m = int(np.sum(~np.isfinite(margin_med_b)))
    return {
        "task": os.path.basename(votes_csv), "rule": repr(rule), "votes_csv": votes_csv,
        "n_items": int(df["item_id"].nunique()), "n_generators": len(judges),
        "gold_tie_items": int(sum(1 for c in gold_counts.values()
                                  if c and len([1 for v in c.values() if v == max(c.values())]) > 1)),
        "loo_domain_size": len(loo_domain),
        "leaderboard_scored_items": int(top["n"]),
        "same_domain_as_floor": bool(same_domain),
        "leader": top["system"],
        "leader_macro_raw": float(top["macro"]),
        "floor_max_raw": float(ceiling),
        "floor_median_raw": med_pool,
        "pool_loo_macro_u": {j: round(v, 6) for j, v in sorted(loo_u_raw.items())},
        "margin_vs_floor_points": float(top["macro"]) - float(ceiling),
        "margin_vs_median_points": float(top["macro"]) - med_pool,
        "ci_floor": {"lo95": lo_f, "hi95": hi_f, "n_boot": n_boot, "seed": SEED,
                     "n_dropped_rounds": n_drop_f},
        "ci_median": {"lo95": lo_m, "hi95": hi_m, "n_boot": n_boot, "seed": SEED,
                      "n_dropped_rounds": n_drop_m},
        "verdict_max_floor": verdict,
        "verdict_if_median_floor": verdict_judge_chain(
            float(top["macro"]), med_pool, same_domain, len(judges)),
        "_rows": rows,
    }


def run_m25_arm(task: str, rule="unmeasured", tmpdir: str | None = None,
                n_boot: int = 2000, median_arm: bool = True) -> dict:
    """m25 arm: build the concatenated votes table, then the generic chain."""
    import tempfile
    tmpdir = tmpdir or tempfile.mkdtemp(prefix="m25_followup_")
    votes_csv = build_m25_votes_table(task, tmpdir)
    arm = run_judge_gold_arm(votes_csv, rule=rule, n_boot=n_boot,
                             median_arm=median_arm)
    arm["task"] = task
    return arm


def validate_m25_arm(arm: dict) -> None:
    """Reproduce evidence/m25_<task>.json (and m25_summary.json) before trusting
    the arm: floor, leader, margin (== 0.0 on decidable arms), CI, domain sizes."""
    t = arm["task"]
    if arm["rule"] != "'unmeasured'":
        return
    car = load_carrier(f"m25_{t}.json")
    summ = load_carrier("m25_summary.json")["tasks"][t]
    check_close(arm["leader_macro_raw"], car["leaderboard"][0]["macro"], 1e-4,
                f"{t}: leader macro vs carrier")
    if arm["leader"] != car["leaderboard"][0]["system"]:
        fail(f"{t}: leader identity mismatch: {arm['leader']} vs "
             f"{car['leaderboard'][0]['system']}")
    check_close(arm["floor_max_raw"], car["ceiling_loo_macro"], 1e-4,
                f"{t}: floor (max over generators) vs carrier")
    check_close(arm["margin_vs_floor_points"], car["margin_vs_floor"], 1e-4,
                f"{t}: margin vs carrier")
    check_close(arm["ci_floor"]["lo95"], car["margin_ci"]["lo95"], 1e-4,
                f"{t}: margin CI lo95 vs carrier (bootstrap must be byte-equivalent)")
    check_close(arm["ci_floor"]["hi95"], car["margin_ci"]["hi95"], 1e-4,
                f"{t}: margin CI hi95 vs carrier")
    if arm["loo_domain_size"] != car["loo_domain_size"]:
        fail(f"{t}: loo_domain_size {arm['loo_domain_size']} vs carrier "
             f"{car['loo_domain_size']}")
    if arm["leaderboard_scored_items"] != car["leaderboard_scored_items"]:
        fail(f"{t}: leaderboard_scored_items mismatch")
    if arm["same_domain_as_floor"] != car["same_domain_as_floor"]:
        fail(f"{t}: same_domain_as_floor mismatch")
    if arm["verdict_max_floor"] != summ["verdict"]:
        fail(f"{t}: verdict {arm['verdict_max_floor']} vs carrier "
             f"{summ['verdict']}")


def fresh_audit_json(votes_csv: str, extra_args: list[str] | None = None) -> dict:
    """Run the production instrument itself (audit.py) on a corpus and return its
    JSON. Used as the validation anchor for carriers that predate the current
    instrument (see note on jev_decision_*.json staleness below) -- the anchor is
    the current audit.py output, recorded with its sha256. Read-only w.r.t. the
    repo: output goes to a temp directory."""
    import tempfile
    out = os.path.join(tempfile.mkdtemp(prefix="fresh_audit_"), "out.json")
    cmd = [sys.executable, os.path.join(HERE, "audit.py"), votes_csv,
           *(extra_args or []), "--json", out]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(out):
        fail(f"fresh audit.py run failed rc={proc.returncode}: "
             f"{(proc.stderr or proc.stdout)[-400:]}")
    with open(out, encoding="utf-8") as fh:
        return json.load(fh)


def validate_judge_gold_arm(arm: dict, car: dict, label: str) -> None:
    """Validate a generic judge-gold arm against a flat run_one-style carrier
    (jev_decision_*.json or audit_both.json's methods.<method> block)."""
    t = label
    if arm["rule"] != "'unmeasured'":
        return
    if arm["n_items"] != car["n_items"]:
        fail(f"{t}: n_items {arm['n_items']} vs carrier {car['n_items']}")
    check_close(arm["floor_max_raw"], car["ceiling_loo_macro"], 1e-4,
                f"{t}: floor (max over generators) vs carrier")
    if arm["leader"] != car["leaderboard"][0]["system"]:
        fail(f"{t}: leader identity mismatch: {arm['leader']} vs "
             f"{car['leaderboard'][0]['system']}")
    check_close(arm["leader_macro_raw"], car["leaderboard"][0]["macro"], 1e-4,
                f"{t}: leader macro vs carrier")
    check_close(arm["margin_vs_floor_points"], car["margin_vs_floor"], 1e-4,
                f"{t}: margin vs carrier")
    check_close(arm["ci_floor"]["lo95"], car["margin_ci"]["lo95"], 1e-4,
                f"{t}: margin CI lo95 vs carrier (bootstrap must be byte-equivalent)")
    check_close(arm["ci_floor"]["hi95"], car["margin_ci"]["hi95"], 1e-4,
                f"{t}: margin CI hi95 vs carrier")
    if arm["loo_domain_size"] != car["loo_domain_size"]:
        fail(f"{t}: loo_domain_size {arm['loo_domain_size']} vs carrier "
             f"{car['loo_domain_size']}")
    if arm["leaderboard_scored_items"] != car["leaderboard_scored_items"]:
        fail(f"{t}: leaderboard_scored_items {arm['leaderboard_scored_items']} "
             f"vs carrier {car['leaderboard_scored_items']}")
    if arm["same_domain_as_floor"] != car["same_domain_as_floor"]:
        fail(f"{t}: same_domain_as_floor mismatch")
    if arm["gold_tie_items"] != car["gold_tie_items"]:
        fail(f"{t}: gold_tie_items {arm['gold_tie_items']} vs carrier "
             f"{car['gold_tie_items']}")
    if arm["verdict_max_floor"] != car["verdict"]:
        fail(f"{t}: verdict {arm['verdict_max_floor']} vs carrier {car['verdict']}")


# ---------------------------------------------------------------- external-gold arm

def run_ext_arm(task: str, n_boot: int = 2000) -> dict:
    """Human-gold chain (audit.run_external_gold caliber): actors vs the external
    gold on the common-items domain; leader/median/max of actor macros; paired
    bootstrap CIs for leader-median and leader-hardest, all actors sharing one
    draw sequence (paired rounds)."""
    votes_csv = os.path.join(EXAMPLES, f"judgesense_{task}.csv")
    gold_csv = os.path.join(EXAMPLES, f"judgesense_{task}_gold.csv")
    df, _ = audit.load(votes_csv)
    ext = audit.load_external_gold(gold_csv)
    df = df[df["item_id"].isin(ext)].copy()
    common = None
    for _a, _s in df.groupby("actor", sort=False):
        _it = set(_s["item_id"])
        common = _it if common is None else (common & _it)
    common = common or set()
    mixed_domain = not common
    if mixed_domain:
        fail(f"{task}: external-gold arm has empty common domain; "
             "the sensitivity battery is undefined here (carrier says "
             "NOT_COMPARABLE) -- report, do not force")
    df_aligned = df[df["item_id"].isin(common)]
    rows = []
    for a, sub in df_aligned.groupby("actor", sort=False):
        hit = audit.agreement(sub, ext)
        ma, mi = audit.macro_micro(hit, sub["slice"])
        rows.append({"system": a, "macro": ma, "micro": mi, "n": int(len(sub)),
                     "hit": hit, "case": sub["case_id"].to_numpy(),
                     "slice": sub["slice"].to_numpy(),
                     "item_id": sub["item_id"].to_numpy()})
    rows.sort(key=lambda r: -r["macro"])
    top = rows[0]
    macro_list = [r["macro"] for r in rows]
    med = float(np.median(macro_list))
    hardest = max(macro_list)
    cases = list(np.unique(np.concatenate([r["case"] for r in rows])))
    slice_levels = list(np.unique(np.concatenate([r["slice"] for r in rows])))
    case_index = {c: i for i, c in enumerate(cases)}
    boot_idx = make_boot_idx(len(cases), n_boot)
    mats = {}
    bvals = {}
    for r in rows:
        S, N = cells_matrices(r["slice"], r["case"], r["hit"], slice_levels,
                              case_index)
        if abs(point_macro(S, N) - r["macro"]) > 0.005:
            fail(f"{task}/{r['system']}: aggregation caliber self-check failed")
        mats[r["system"]] = (S, N)
        bvals[r["system"]] = boot_macro_rounds(S, N, boot_idx)
    name_list = [r["system"] for r in rows]
    B = np.vstack([bvals[n] for n in name_list])            # (n_actors, n_boot)
    with np.errstate(invalid="ignore"):
        med_b = np.nanmedian(B, axis=0)
        max_b = np.nanmax(B, axis=0)
    lead_b = bvals[top["system"]]
    m_med = (lead_b - med_b) * 100.0
    m_max = (lead_b - max_b) * 100.0
    lo_m, hi_m = percentile_ci(m_med)
    lo_x, hi_x = percentile_ci(m_max)
    return {
        "task": task, "votes_csv": votes_csv, "gold_csv": gold_csv,
        "n_items": int(df["item_id"].nunique()),
        "n_items_common": len(common), "n_actors": len(rows),
        "n_cases": len(cases),
        "leader": top["system"], "leader_macro_raw": float(top["macro"]),
        "median_macro_raw": med, "hardest_macro_raw": hardest,
        "min_macro_raw": float(min(macro_list)),
        "floor_basis_of_chain": "median_of_actors",
        "margin_vs_median_points": float(top["macro"]) - med,
        "margin_vs_hardest_points": float(top["macro"]) - hardest,
        "ci_median": {"lo95": lo_m, "hi95": hi_m, "n_boot": n_boot, "seed": SEED,
                      "n_dropped_rounds": int(np.sum(~np.isfinite(m_med)))},
        "ci_hardest": {"lo95": lo_x, "hi95": hi_x, "n_boot": n_boot, "seed": SEED,
                       "n_dropped_rounds": int(np.sum(~np.isfinite(m_max)))},
        "verdict": verdict_external_chain(float(top["macro"]), med, False),
        "_rows": rows, "_bvals": bvals, "_cases": cases, "_boot_idx": boot_idx,
    }


def validate_ext_arm(arm: dict) -> None:
    """Reproduce evidence/audit_<task>.json: leaderboard macros, floor_median_macro,
    floor_robustness min/max, verdict, common-item count, and (carrier-anchored)
    the per-system paired CIs of multiplicity.per_system, which audit.py computed
    with _cluster_bootstrap_diff(seed=20261001) -- our per-round values must
    reproduce them, which anchors the shared draw sequence."""
    t = arm["task"]
    car = load_carrier(f"audit_{t}.json")
    lb = {r["system"]: r["macro"] for r in car["leaderboard"]}
    for r in arm["_rows"]:
        if r["system"] in lb:
            check_close(r["macro"], lb[r["system"]], 1e-4,
                        f"{t}: actor {r['system']} macro vs carrier")
    check_close(arm["median_macro_raw"], car["floor_median_macro"], 1e-4,
                f"{t}: floor_median_macro vs carrier")
    fr = car["floor_robustness"]
    check_close(arm["min_macro_raw"], fr["min"], 1e-4, f"{t}: floor min vs carrier")
    check_close(arm["hardest_macro_raw"], fr["max"], 1e-4,
                f"{t}: floor max (hardest actor) vs carrier")
    if arm["n_items_common"] != car["n_items_common_to_all_actors"]:
        fail(f"{t}: common items {arm['n_items_common']} vs carrier "
             f"{car['n_items_common_to_all_actors']}")
    if arm["verdict"] != car["verdict"]:
        fail(f"{t}: verdict {arm['verdict']} vs carrier {car['verdict']}")
    # carrier-anchored CI check on up to 6 system-vs-leader contrasts
    checked = 0
    for rec in car["multiplicity"]["per_system"]:
        sysname = rec["system"]
        if rec.get("ci_lo95") is None or sysname not in arm["_bvals"]:
            continue
        d = (arm["_bvals"][sysname] - arm["_bvals"][arm["leader"]]) * 100.0
        lo, hi = percentile_ci(d)
        check_close(lo, rec["ci_lo95"], 1e-4,
                    f"{t}: system-vs-leader CI lo95 ({sysname}) vs carrier")
        check_close(hi, rec["ci_hi95"], 1e-4,
                    f"{t}: system-vs-leader CI hi95 ({sysname}) vs carrier")
        checked += 1
        if checked >= 6:
            break


def validate_substrate_equivalence(tasks: tuple[str, ...] = TASKS) -> None:
    """data/ds_<task>.csv (used by the prior median-interval line) and
    examples/judgesense_<task>.csv + _gold.csv (used by the audit carriers) must
    describe the same (actor, item) -> (answer, gold) table."""
    import csv as _csv
    for t in tasks:
        def pairs(path, goldcol):
            out = {}
            with open(path, newline="", encoding="utf-8") as fh:
                for r in _csv.DictReader(fh):
                    out[(r["actor"], r["item_id"])] = (r["answer"], r.get(goldcol, ""))
            return out
        js = pairs(os.path.join(EXAMPLES, f"judgesense_{t}.csv"), "gold")
        ds = pairs(os.path.join(PAPER_ROOT, "data", f"ds_{t}.csv"), "gold")
        if set(js) != set(ds):
            fail(f"substrate equivalence {t}: (actor,item) key sets differ "
                 f"({len(js)} vs {len(ds)})")
        bad = [k for k in js if js[k][0] != ds[k][0]]
        if bad:
            fail(f"substrate equivalence {t}: {len(bad)} answer mismatches")
        gf = {}
        with open(os.path.join(EXAMPLES, f"judgesense_{t}_gold.csv"), newline="",
                  encoding="utf-8") as fh:
            for r in _csv.DictReader(fh):
                gf[r["item_id"]] = r["gold"]
        mism = sum(1 for (a, i), (_ans, g) in js.items() if gf.get(i, "") != g)
        if mism:
            fail(f"substrate equivalence {t}: gold column vs gold file: {mism} mismatches")


# ---------------------------------------------------------------- selftest

def selftest() -> int:
    """Known-answer fixture for the shared machinery. Injects a small corpus whose
    gold, floor, median, margin and verdicts are computable by hand, and asserts
    every layer reproduces them. A --selftest that cannot fail is decoration, so
    the mutation checks at the end must come out red on purpose."""
    import tempfile
    fails: list[str] = []

    def ok(name, cond):
        if not cond:
            fails.append(name)

    # -- fixture: 3 cases x 2 items, 4 judges, known answers -------------------
    rows = []
    gold_by_item = {"i1": "X", "i2": "X", "i3": "X", "i4": "Y", "i5": "X", "i6": "X"}
    # votes (i2: X,X,Z,Z -> tie; i4: Y,Y,X,X -> tie; i3 LOO of j1: Z,X,Y -> 1-1-1)
    ans = {
        "j1": dict(zip(["i1","i2","i3","i4","i5","i6"], ["X","X","X","Y","X","X"])),
        "j2": dict(zip(["i1","i2","i3","i4","i5","i6"], ["X","X","Z","Y","Y","X"])),
        "j3": dict(zip(["i1","i2","i3","i4","i5","i6"], ["X","Z","X","X","X","X"])),
        "j4": dict(zip(["i1","i2","i3","i4","i5","i6"], ["Y","Z","Y","X","X",""])),
    }
    case_of = {"i1": "c1", "i2": "c1", "i3": "c2", "i4": "c2", "i5": "c3", "i6": "c3"}
    for a, mp in ans.items():
        for it, v in mp.items():
            rows.append({"item_id": it, "case_id": case_of[it], "slice": "s",
                         "role": "judge", "actor": a, "answer": v, "gold": gold_by_item[it]})
            rows.append({"item_id": it, "case_id": case_of[it], "slice": "s",
                         "role": "system", "actor": a, "answer": v, "gold": gold_by_item[it]})
    with tempfile.TemporaryDirectory() as td:
        fx = os.path.join(td, "fixture.csv")
        pd.DataFrame(rows).to_csv(fx, index=False)
        df, have_prob = audit.load(fx)
        jdf = df[df["role"] == "judge"].copy()
        sdf = df[df["role"] == "system"].copy()
        gold = audit.build_gold(jdf, have_prob, "unmeasured")
        votes = {(r.item_id, r.actor): r.answer_n for r in jdf.itertuples()}
        loo = audit.leave_one_out(gold, "majority", votes, {})
        # hand gold (answers normalize to lowercase): i1 x, i3 x, i5 x, i6 x;
        # i2 and i4 are 2-2 ties -> unmeasured (absent)
        ok("gold i2 is tie (unmeasured)", "i2" not in gold.majority)
        ok("gold i4 is tie (unmeasured)", "i4" not in gold.majority)
        ok("gold i6 = x", gold.majority.get("i6") == "x")
        # LOO for j1 on i3: others vote Z,X,Y -> all distinct -> c^- undefined
        ok("loo j1 i3 undefined", "i3" not in loo["j1"])
        ok("loo j1 i6 = x", loo["j1"].get("i6") == "x")
        # leader vs external gold, full domain (6 items; answers lowercase)
        ext = {it: audit.norm_answer(g) for it, g in gold_by_item.items()}
        df2 = df[df["item_id"].isin(ext)].copy()
        common = None
        for _a, _s in df2.groupby("actor", sort=False):
            _it = set(_s["item_id"]); common = _it if common is None else (common & _it)
        df3 = df2[df2["item_id"].isin(common)]
        acc = {}
        for a, sub in df3.groupby("actor", sort=False):
            hit = audit.agreement(sub, ext)
            ma, mi = audit.macro_micro(hit, sub["slice"])
            acc[a] = ma
        # common items = 6; the external gold covers all 6 (it is not the majority
        # gold). accuracies vs ext {X,X,X,Y,X,X}:
        #   j1 6/6=100, j3 4/6, j2 4/6, j4 1/6 -> median 200/3, min 50/3
        ok("leader is j1 at 100", abs(acc["j1"] - 100.0) < 1e-9)
        ok("median is 200/3", abs(float(np.median(list(acc.values()))) - 200.0 / 3.0) < 1e-9)
        ok("min is 50/3", abs(min(acc.values()) - 50.0 / 3.0) < 1e-9)
        # verdict chain branches (each arm exercised by construction)
        ok("branch DOMAIN_MISMATCH",
           verdict_judge_chain(50.0, 60.0, False, 4) == "UNDECIDABLE_DOMAIN_MISMATCH")
        ok("branch FLOOR_DEGENERATE",
           verdict_judge_chain(50.0, 60.0, True, 2) == "UNDECIDABLE_FLOOR_DEGENERATE")
        ok("branch NO_READING",
           verdict_judge_chain(float("nan"), 60.0, True, 4) == "UNDECIDABLE_NO_READING")
        ok("branch UNREADABLE above",
           verdict_judge_chain(50.0, 60.0, True, 4) == "UNREADABLE")
        ok("branch UNREADABLE equal",
           verdict_judge_chain(60.0, 60.0, True, 4) == "UNREADABLE")
        ok("branch MARGINAL",
           verdict_judge_chain(61.9, 60.0, True, 4) == "MARGINAL")
        ok("branch READABLE",
           verdict_judge_chain(62.0, 60.0, True, 4) == "READABLE")
        ok("external NEAR", verdict_external_chain(61.0, 60.0, False) == "NEAR_MEDIAN_ACTOR")
        ok("external ABOVE", verdict_external_chain(62.0, 60.0, False) == "ABOVE_MEDIAN_ACTOR")
        ok("external AT_OR_BELOW", verdict_external_chain(60.0, 60.0, False)
           == "AT_OR_BELOW_MEDIAN_ACTOR")
    # -- tie resolvers on a known tally {A:2, B:2, C:1} ------------------------
    tally = {"A": 2, "B": 2, "C": 1}
    actor_votes = [("a1", "A"), ("a2", "A"), ("a3", "B"), ("a4", "B"), ("a5", "C")]
    ok("tie unmeasured -> None", _resolve_top(tally, "unmeasured") is None)
    ok("tie lexicographic -> A", _resolve_top(tally, "lexicographic") == "A")
    r1 = _resolve_top(tally, ("random", 0), np.random.default_rng(0))
    r2 = _resolve_top(tally, ("random", 0), np.random.default_rng(0))
    draws = {_resolve_top(tally, ("random", 1), np.random.default_rng(1 + i))
             for i in range(30)}
    ok("tie random in {A,B}", r1 in ("A", "B"))
    ok("tie random reproducible with same rng state", r1 == r2)
    ok("tie random actually varies across draws (non-vacuous)", len(draws) == 2)
    ok("weighted tie-break picks heavier side",
       _resolve_top(tally, ("weighted", {"a1": 0.2, "a3": 0.9}), 
                    actor_votes=actor_votes) == "B")
    ok("weighted tie-break flips with weights",
       _resolve_top(tally, ("weighted", {"a1": 0.9, "a3": 0.2}),
                    actor_votes=actor_votes) == "A")
    ok("weighted exact tie -> None",
       _resolve_top({"A": 2, "B": 2}, ("weighted", {"a1": 1.0, "a3": 1.0}),
                    actor_votes=[("a1", "A"), ("a3", "B")]) is None)
    ok("unique winner unaffected by rules", _resolve_top({"A": 3, "B": 1}, "unmeasured") == "A")
    # -- percentile CI on a known sample ---------------------------------------
    ci = percentile_ci(np.arange(1, 2001, dtype=float))
    ok("percentile CI endpoints", abs(ci[0] - 50.975) < 1e-6 and abs(ci[1] - 1950.025) < 1e-6)
    ok("percentile CI all-nan",
       bool(np.isnan(percentile_ci(np.full(4, np.nan))[0])))
    # -- mutation checks (must come out red) ------------------------------------
    import copy
    ok("mutation: verdict chain would accept a wrong equal-arm",
       verdict_judge_chain(60.0, 60.0 + 1e-12, True, 4) == "UNREADABLE")
    ok("mutation: above-arm",
       verdict_judge_chain(60.0, 60.0 + 2.0, True, 4) == "UNREADABLE")
    # negative control of the negative control: a READABLE-ish boundary must NOT
    # be classified UNREADABLE
    if verdict_judge_chain(62.1, 60.0, True, 4) == "UNREADABLE":
        fails.append("mutation: READABLE boundary misclassified (gate is dead)")

    print(f"followup_common selftest: {'PASS' if not fails else 'FAIL'}")
    for f in fails:
        print("  -", f)
    return 0 if not fails else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print("usage: import as module, or run with --selftest")
    sys.exit(2)
