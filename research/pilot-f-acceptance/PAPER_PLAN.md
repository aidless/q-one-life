# PAPER_PLAN.md — f-acceptance / The Name Is the Contract

Generated 2026-10-30. This file is the plan the draft already follows, reconstructed from the draft: it is a *reconciliation*, not a promise about work not yet done.

## What this paper argues

From the draft's own abstract, verbatim (source `source/main.tex`):

> A self-improving agent system accepts a candidate variant through an acceptance rule, and the rule's name is the interface every downstream consumer reads. We audit one such rule: a function named \code{mcnemar\_exact} that gates self-evolution promotion via \code{promote = bool(new\_wins > old\_wins and p < 0.05)}. Its docstring admits the body's reality (exact below $n{=}25$, normal approximation otherwise), but the name advertises a rigour the body does not honour. Recomputing the entire fallback region ($n{=}26\ldots500$, $b\ge c$: 62{,}819 cells, of which the gate would promote 55{,}469) against the level-matched exact reference (\code{scipy.stats.binomtest}, two-sided) yields 231 decision flips at $\alpha{=}0.05$, and every one favors promotion *relative to that reference*. The fallback is an uncorrected normal approximation; the one-line continuity correction replaces those 231 promotion-side flips with 9 of the opposite sign, on a disjoint set of cells, while mid-p leaves 221 anti-conservative against the same exact reference: the fix is a dial, not a restore. The largest absolute error is $0.152610$ at $b{=}14$, $c{=}13$ ... A workspace-wide classifier finds 118 name-matched function ...

## Section plan, as the draft implements it

1. **Introduction** — the name-as-interface framing; the audit question.
2. **The gate under audit** — the function, its docstring, the promotion rule (C01).
3. **F-01: the approximation is one-sided — relative to its reference** — the 62,819-cell recomputation, 231 flips (C01, C02, C03, C04, C05, C13).
4. **F-02: one file, or a pattern?** — the workspace-wide classifier (C07).
5. **Dynamic validation of the classifier's positive claims** — the dynamic audit across targets (C08).
6. **Two defects in our own tools** — self-audit.
7. **What the exit code means** — semantics of the gate.
8. **Gate status** — the current gate's standing.
9. **Related work** — position against exact/reference testing literature.
10. **What this does not establish** — scope limits (C11).
11. **Conclusion** — the audit outcome.
12. **Reproduction and data availability** (appendix).

## How the numbers in it were checked

`validation_path: bounded_subset_rerun` — 134 printed numbers re-derived; ~130 bound (97%), 2 non-data, 2 derived. 13 native ledger entries (C01-C13), all verified except C10 (candidate) / C11 (blocked — needs independent re-review bound to source hash `986c0a30...`).

## Evidence Record

- **live draft**: `source/main.tex` (SHA-256 `986c0a3039e91dc31ad182a2fdaaba643454edd61407b8cfb280c64ef244d5ef`)
- **Claim Ledger**: `CLAIM_LEDGER.md` (13 entries C01-C13)
- **native evidence**: `evidence/native/wave2-F-acceptance/revision_stats.json` (C01-C06), `evidence/native/wave2-F-acceptance/flip_band.json` (C05), `evidence/native/wave2-F-acceptance/github_survey/raw/` (C07), `evidence/native/wave2-F-acceptance/dynamic_audit_frozen200.json` (C08), `evidence/native/data/f02_gate_inventory.json` (C07)
- **independent review**: `evidence/reviews/FINAL_REVIEW_2026-10-26.md` (C11 — blocked until bound to current source)
- **validation_path basis**: `bind_numbers_tool.py --run` (re-executed)

## Notes for the drafting phase

- **C11 (independent re-review bound to current source) remains blocked.** Any prose that treats the review as closed must be held until the receipt exists.
- The "fix is a dial, not a restore" finding and the disjointness of the two flip sets (C13) are the core contributions.
- No new numeric claim without a registered evidence field.
