# Review Round 6 (formal `/research-review` 3/3 followup, 2026-09-10)

Formal round 3 verdict was WARN with one major: T30 dual-source (24/120 per-seed
JSONs disagree with CSV/summary; B:18/C:5/D:1). Independently re-verified exactly.

## Root cause
CSV/summary built 09-04 19:30 from a partially different run set; 24 seeds'
JSONs differ (one, B_seed012, modified after analysis at 19:40). Headline table
matched the stale side; window tests matched the JSON side.

## Single-source regen (author-method-faithful)
- Canonical source: 120 per-seed JSONs. Script:
  `evidence/regen_T30_singlesource_20260910.py` (pinned in manifest).
- Conventions recovered EXACTLY on zero-drift condition A: acc = mean of
  per-agent means; gamma_final = per_round[-1].gamma; std ddof=0;
  main-effect p = Student's t; d = pooled ddof=0.
- interaction p: original method unrecoverable (no standard test reproduces the
  old pins) -> recomputed via standard 2x2 ANOVA F, df=(1,116). Explicit change.
- Validation: 96/120 rows reproduce within 1e-9 (44 differ only at 1e-16 repr);
  24 real diffs. Conclusions unchanged (overall null holds everywhere).

## Manuscript updates (11)
tab:joint_overall B/C/D rows (+D gamma 1.129->1.128); L465 bounds p>0.12/d<0.29;
L483 full ANOVA sentence; L47 abstract bound; single-source disclosure sentence;
late-phase means (gamma 0.637/0.605; H 0.916/0.925 -- reviewer said 0.923, but
per-seed recompute gives 0.9248 and the quoted d/p match the recompute, so the
reviewer's eyeball was off by 0.002); strategy weights 0.187/0.161.

## Manifest
Refreshed 2 pins + regen script pinned: 616 -> 617, note history extended.
Backups: `.bak.reviewR6.*`.
