# EVIDENCE_PLAN — tmlr-paper13-merged (B1 carrier gate)

Scope of this pass: the 24 headline numbers the carrier gate reports as
`unbacked` for this run (inventory entry `tmlr-paper13-merged`, `verdict=UNBACKED`).
The author's source project `/data3/Research/PAPER13_MERGED` and this run's
`source/evidence/` carriers were opened and every flagged value was either
re-derived from a delivered artifact or proven absent.

**Comparison rule.** A number is *backed* when a delivered artifact either
(i) stores a value equal to the paper value within `|Δ| ≤ 5e-4`, or
(ii) stores a value that rounds to the paper's displayed precision
(`round(carrier, paper_dp) == paper`), or
(iii) the paper value is re-computable from the artifact's raw leaves by the
formula the manuscript itself states, matching under (i)/(ii).
`grep`-substring hits are NOT treated as backing; numeric leaves were extracted
recursively and compared by value.

---

## 1. Headline numbers now backed by a verified carrier (2 of 24)

| # | Paper value | `source/main.tex` line | Meaning | Carrier file | JSON path / cell | Value found | Agree | Rule |
|---|---|---|---|---|---|---|---|---|
| 1 | `2.94` | `main.tex:444` | CNR upper bound `= γ̄ / CV` for the n=30 uncalibrated E4 archive | `evidence/e4_n15_results.json` + `evidence/e4_30seed_calibrated.json` | `results.uncalibrated[].gTV` (n=30); `uncalibrated.gTV` | γ̄=1.08114 (carrier gTV=1.0811), sd(ddof1)=0.39801 → CV=0.3681, bound=**2.9368** | **YES** | round(2.9368,2)=2.94 |
| 2 | `2.31` | `main.tex:742` | full-archive per-seed CV of the *DS×Qwen (qwen eval)* condition, Monitor case | `evidence/analyses/p1c_monitor_case_20260808.json` | `rows[condition="DS x Qwen (qwen eval)"].CV` | **2.306** | **YES** | round(2.306,2)=2.31 |

Re-derivation is reproducible by a reviewer with
`evidence/scripts/verify_b1_headline_20260926.py` (run from `evidence/`); its
stored output is `evidence/analyses/b1_headline_recheck_20260926.json`.
The companion Monitor value `5.48` (L742, DS Self-Eval) is likewise `5.477` in
the same file and rounds correctly — recorded here because it corroborates the
`2.31` row; it was not on the gate list.

---

## 2. Numbers that could NOT be placed (22 of 24) — search record by reason class

### Class A — source experiment not archived in the package (10 values)
Table `tab:sync-pairs` (`main.tex:188–198`), the 13-condition study's four
sync/nosync CAF pairs and their 95% bootstrap CIs:
`1.243, 1.350` (C5 real-image points) and CI endpoints `1.416, 1.087, 1.035,
1.204, 1.518, 0.858, 0.797, 0.778`.
- **Searched:** every JSON in `/data3/Research/PAPER13_MERGED/**` (recursive
  numeric-leaf scan, tol 5e-4) — 0 matches for any of these as a CAF;
  `supplementary.zip` (64 files) — mirrors `source/evidence/`, no extra data;
  `evidence/canonical_results_v5.json` (72 cells), `archived_joint_2x2_30seed`
  (explicitly labelled "NOT the basis of the manuscript's main claims"),
  `e4_*`, `joint_full_F_v10`. None is the 13-condition CAF source.
- **Missing:** the raw per-seed records of the 13-condition sync/nosync study
  that would regenerate CAF and its bootstrap CI. They are not in the run and
  not in the author's project. This is the same corpus the paper's
  `reserved-evidence-url` ("anonymised repository … will be populated at
  camera-ready") defers; the flagship `ΔCAF = -0.107` = `1.243 − 1.350`
  (`main.tex:197`, `main.tex:214`) therefore has no carrier, and the
  `claims.yaml` C01 pointer (`canonical_results_v5.json`, `0.gamma_mean=0.1443`)
  names a different quantity (α=0/τ=0.5/method=none cell mean), not the ΔCAF.

### Class B — Finding-1 per-repetition ECE never generated (7 values)
Calibration-contagion `2×2` ANOVA table A.2 (`main.tex:826–829`) and the
decomposition d (`main.tex:349/630`): `4.180, 660.20, 0.0172, 0.0075, 0.0058,
2.265, 4.70`.
- **Searched:** full-tree numeric-leaf scan — 0 stored matches (the 0.0058 /
  0.0172 leaf hits are unrelated `MCE_post`/`total_delta_H` quantities, not
  ANOVA sums of squares); `reports/hallucination_20260819.md:9` records the
  named method file `evidence/finding1_eight_conditions.json` as missing.
- **Missing:** the eight-condition per-repetition ECE log (per-round grid,
  `df=358`). The manuscript itself discloses this at `main.tex:366`
  ("the per-repetition ECE records underlying this decomposition were not
  archived … not independently recomputable from the delivered evidence") and
  `evidence/FINDING1_DATA_SEARCH_VERDICT.md` (8 search rounds) plus
  `claims.yaml` INCON-ARCHIVE-01 confirm the CSV was never generated and the
  release copy was synthetic. Because it is honestly disclosed, this class is a
  known archival gap, not a live presentational defect; it nonetheless remains
  unbacked.
- Consistency note (not a re-derivation, since the inputs are absent): the A.2
  table is internally consistent — `MS_T/MS_err = 4.180/(2.265/358)=660.7 ≈ 660.20`,
  `0.0172/(2.265/358)=2.72 ≈ 2.71`, `0.0058/(2.265/358)=0.92`.

### Class C — within-condition per-seed landscape weights absent (2 values)
`main.tex:158` / `main.tex:627`: `0.912` (DS×Qwen within-condition `r(γ,H)`,
stated "recomputed from archived per-seed weights") and `0.842` (lower end of
the corrected 11-condition leave-one-out range `[-0.992,-0.842]`).
- **Searched:** the only per-seed γ/H archive delivered is
  `evidence/archived_joint_2x2_30seed_20260811.json`. Recomputing per-seed
  Pearson `r(γ,H)` from `final_gamma_mean_per_rep`/`final_H_per_rep` for its
  four conditions A/B/C/D gives `-0.151 / -0.761 / -0.151 / -0.151` — not
  `-0.912` nor the companion `-1.000`. The 11-condition landscape table is
  referenced to a "companion manuscript" and is not in the package.
- **Missing:** the DS-self-eval (N=30) and DS×Qwen (N=30) per-seed weight/γ/H
  arrays and the corrected 11-condition table. `landscape_5conditions.json`
  carries only the aggregate `r=-0.989 / -0.916`, not the within-condition or
  leave-one-out values.

### Class D — carrier delivered but statistic not reproducible (1 value)
`main.tex:164`: `2.98` — paired `t` for "τ suppresses the γ advantage of
confidence gating over the no-calibration baseline across four α levels".
- **Searched / recomputed from** `canonical_results_v5.json`: the delivered
  carrier holds the raw `gamma_mean` per (α,τ,method). The advantage
  `γ(conf_gating) − γ(none)` per α, paired across τ (4 df=3 pairs) gives
  `t = 3.12` (τ 0.5 vs 2.0) / `t = 3.22` (τ 0.5 vs 1.0); no natural
  definition reproduces `t = 2.98` (p=0.030). Under this paper's own rule this
  is "carrier exists but disagrees" — recorded as unbacked with a reproduction
  mismatch, though the test definition in the prose is ambiguous.

### Class E — derived from unbacked approximations (1 value)
`main.tex:364`: `0.942` — the "relative Δaccuracy" ratio in `0.65 / 0.69`.
- **Searched:** 0.65 and 0.69 are approximate accuracies of the Finding-1
  conditions (Class B source, not archived); the ratio 0.65/0.69=0.9420 is
  arithmetic on values that themselves have no carrier. No stored 0.942.

### Class F — stochastic subset-sensitivity endpoint (1 value)
`main.tex:836` / `main.tex:868`: `3.19` — upper end of `F_α` range `[0.04,3.19]`
from 200 random 15-per-cell subsets of the 125-session joint archive
(`joint_full_F_v10_results.json`).
- **Reproduced:** an independent 200-draw subset-sensitivity (seed 42) over the
  T∈{10,20} cells gives median `0.575`, range `[0.012, 3.297]`, and the
  balanced 15-per-cell `F_α = 6.610` matching the paper's stated "balanced
  recomputation F_α=6.61" exactly. The bracket and the balanced value are
  reproduced, but the specific endpoint `3.19` is RNG-seed-dependent (mine
  reached 3.297); the author's subset seed is not recorded, so `3.19` cannot be
  matched to `|Δ| ≤ 5e-4`. Classified unbacked-by-exact-value, procedure sound.

### Class G — carrier's own ANOVA summary has no derivation inside the package (5 values)
`main.tex:65` (abstract), `:637`, `:654`, `:656`, `:660`, `:763` and the mirrored
lines in `runs/tmlr-paper1-consolidated/paper/main.tex:67,564,581,583,587,683`:
`F_α = 8.16 (p = 0.0006)`, `F_T = 7.845 (p = 0.0063)`,
`F_interaction = 15.37 (p < 0.0001)`, `SS_within = 2.8975`,
`MS_within = 0.03449`, plus the effect size `d ≈ 0.3 (p = 0.001)` at `:656`.
- **The carrier does ship them** — in `joint_full_F_v10_results.json`
  `summary.anova_ECE`, not among the 24 values the gate flags, which is why this
  class was missed until the block itself was audited.
- **Self-consistent:** every stored quantity agrees with every other
  (`SS = MS·df`, `F = MS/MS_within`, `p` reproduced from `F` under `df(2,84)` /
  `df(1,84)`). So this is not an arithmetic error.
- **Not derivable from the delivered sessions.** Under the manuscript's own
  documented subset ("first 15 completed sessions per cell, ascending cell index
  then seed") the recomputation gives `F_α = 6.610 (p = 0.0022)`, `F_T = 2.951
  (p = 0.089)`, `F_interaction = 2.219 (p = 0.115)`. The published `6.61 / 0.0022`
  is reproduced exactly; `8.16`, `7.845`, `15.37` are not reproduced under that
  subset or any other ordering (`F_α` ranges 0.012–6.61 across five defensible
  orderings).
- **Proven unreachable, not merely unreproduced.** `final_ECE` takes only three
  values `{0.5, 0.75, 1.0}`, so the sum of squares reachable by any 15-per-cell
  subset is a finite set of exact rationals. The three cells with exactly 15 rows
  are forced in and contribute `287/120 = 2.391666…`; the remaining three cells
  would have to contribute `607/1200 = 0.505833…`, which is **not** in the
  124-value reachable set (nearest `0.508333…`, distance 0.0025). No subset of the
  delivered rows can yield `SS_within = 2.8975`.
- **Separate inconsistency in the same block:** `summary.cell_table_ECE_mean`
  matches the cell means of all 115 archived `T∈{10,20}` sessions cell-for-cell,
  while `summary.anova_ECE` declares `n_per_cell = 15` and `df_within = 84 = 90−6`.
  The cell table is built from 115 rows and the ANOVA from 90; the two parts of one
  summary block cannot share a source.
- **Audit tool:** `tools/recompute_joint_anova.py` (exit 0 reproduced / 2 not
  reproduced / 3 skip), report `inventory/joint_anova_recompute.json`, negative
  controls `tests/test_recompute_joint_anova.py`. Full write-up:
  `HANDOFF_20261001T2050Z_joint_anova_recompute.md`.
- **Consequence:** `F_α = 8.16` currently carries the run's headline claim that
  pre-registered P3 was refuted (`:654`, `:656`). The reproducible value `6.61`
  has the same direction but a different magnitude; `F_T` and the interaction are
  non-significant under the reproducible subset. Closing this needs either a
  disclosed downgrade or a rerun that archives per-repetition ECE
  (`runs/SCHEDULE_20261001T2020Z_experiment_schedule.md`, wave 3).

---

## 3. Staged additions this pass (new files only; nothing overwritten)
- `evidence/scripts/verify_b1_headline_20260926.py` (3,231 B) — regenerates the
  two verified headline numbers from their existing carriers.
- `evidence/analyses/b1_headline_recheck_20260926.json` (945 B) — stored
  re-derivation output.

The verified numbers' raw carriers (`e4_n15_results.json`,
`e4_30seed_calibrated.json`, `analyses/p1c_monitor_case_20260808.json`) already
ship in this package, so no bulk copy was made; a regeneration script plus its
output is the reviewer-runnable proof. Neither `evidence_manifest.json` was
edited (out of scope per task).

## 4. Note on `reserved-evidence-url`
The manuscript's anonymised-repository commitment ("reserved and will be
populated at camera-ready") is an honest future-tense statement, not a defect.
Because the files staged here are what a reviewer actually receives, the Class
A / C gaps above are the concrete consequence: the headline CAF and
within-condition-correlation numbers cannot be checked against anything in the
delivered package today.
