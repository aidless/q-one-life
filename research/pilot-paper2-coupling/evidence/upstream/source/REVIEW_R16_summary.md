# Adversarial review R16 — PAPER2_CONSOLIDATED

Decision: **Major Revisions**.

Canonical-scope numeric rerun (excluding evidence, reviews, tests, and build
scaffolding) found no inverted confidence intervals, but four stale anonymous-URL
markers, 71 evidence-only values, and 25 table/prose mismatches. Several mismatches
come from parallel manuscript variants (`main.tex`, `main_v9.tex`, `main_arxiv.tex`,
`main_nb.tex`); these must be reduced to one canonical submission source before
Strong-Accept consideration.

Critical: (1) 11-condition empty-regime claim is not a universal impossibility result; (2) tight-bound calibration and validation reuse the same data. Major: proof gaps in T1–T3, gamma parameter mismatch, missing standard evaluator baselines, CV(N=5) vs N=30 inconsistency, omitted conditions/CIs, and weak GPT-4o snapshot provenance. These reproduce the existing multi-reviewer meta-review and remain open.
## Revision R17 (2026-08-19)

- Fresh canonical compile of `main.tex` succeeded (exit code 0; PDF generated in `sa_20260819_b`) with no undefined-citation warnings.
- Canonical citation coverage is complete. Whole-tree scan residuals are confined to noncanonical `main_arxiv.tex` and a documentation-path token; these are excluded from the submission tree.
- The canonical manuscript keeps the empty-region result, bound, and empirical associations explicitly conditional; no universal-impossibility claim was promoted.
- Major blockers remain proof assumptions, circular tight-bound validation, omitted condition rows, evaluator baselines, sample-size harmonization, GPT-4o provenance, and clean single-source packaging.
