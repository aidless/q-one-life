# Independent Review: pilot-paper11 / Harness Selection

Review type: method and statistics, read-only evidence review (scientific-reviewer subagent, 2026-10-30)

Reviewer: scientific-reviewer subagent (independent context, no prior)

## Frozen target

- Project: `research/pilot-paper11`
- Manuscript: `source/main.tex` (SHA-256 9748c64cbd338dcc ✓)
- Claim Ledger: `CLAIM_LEDGER.md` (C01-C20)
- Evidence: `evidence/paper11-matched-analysis.json`, `evidence/candidate-manifest.json`, `evidence/score-recompute.json`, `evidence/order-contract.json`

## Per-claim verdicts

- **C03 supported** — 7/30=23.33%, Wilson 95% CI recomputed 11.79%–40.93% (matches ledger 23.3%/11.8%/40.9%). Macro \ScoreAChoiceRate=23.3%, \ScoreAChoiceCI=11.8% to 40.9% match.
- **C04 supported** — 5/30=16.67%, CI recomputed 7.34%–33.56% (matches 16.7%/7.3%/33.6%). Macro matches.
- **C07 supported** — 15/30=50.0%, CI recomputed 33.15%–66.85% (matches 50.0%/33.2%/66.8%). Score outcome (mean −0.0222, CI −0.1000 to 0.0333) consistent; correctly not claimed as nonzero.
- **C09 supported** — 60/60 top-scored (nontied 12/12). Framed as instrument check, not mechanism.
- **C13 supported** — candidate-manifest: 90 entries, 0 missing; score-recompute: 90/90 expected, 0 mismatch, 0 missing, all match=true.
- **C20 supported** — order-contract: 23/30 mismatches, repair_binding_present=true; source_provenance: old_diff=23, repair_changed=11, scope="Only the hard arm was recalled; all other arm outcomes were reused byte-for-byte."

## Checklist (a-e)

- (a) Field correspondence: all 6 ledger field paths resolve to real JSON keys; no dangling refs.
- (b) Number recompute: all counts reproduced (7/30, 5/30, 15/30, 60/60, 90/90+0, 23/30+11). All match generated_values.tex.
- (c) Method: Wilson (z=1.96); paired-task percentile bootstrap 20000 draws seed 20261027; task seed 20261023. Appropriate for descriptive within-sample audit.
- (d) Confounds: interface-audit vs quality-inference separation drawn; rubric "outcome, not a referee"; limitations enumerate model/order pair, deterministic selection, coarse benchmark, no population inference.
- (e) Result vs inference: descriptive with n and CIs; Conclusions/Limitations cap at "local and descriptive"; strong-claim register removes position-bias/generalization/ground-truth claims.

## Overall verdict

**supported (all 6 claims verified; no revision warranted)**

## Residual observations (non-blocking)

1. Ledger CI values are 1-dp-rounded; exact recompute agrees (11.79-40.93, 7.34-33.56, 33.15-66.85).
2. C07 delta includes 0 — correctly not claimed as nonzero quality effect.
3. C20 repair is a transparently disclosed internal-consistency correction, not a quality claim.
4. All ledger statuses verified and all macros cross-check, confirming the manuscript renders the audited numbers.
