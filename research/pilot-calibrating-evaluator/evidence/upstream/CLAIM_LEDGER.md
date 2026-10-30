# Claim ledger — tmlr_p9

| ID | 声明 | 证据文件+字段 | 数值 | 如何验证 | 状态 |
|---|---|---|---|---|---|
| C01 | Canonical manuscript defines standard binary TTRL and confidence-weighted calibrated TTRL, including a 10-round sliding isotonic window. | calibrated_ttrl.py | protocol description | Audit code and freeze exact prompt/update implementation | verified |
| C02 | Abstract reports a within-subjects N=5 comparison and 20–49% gamma / 45–67% JSD reductions. | evidence/scope_C02_C03.md | 20-49% gamma /45-67% JSD pilot descriptive (no JSON), hedged | Recompute from immutable per-seed outputs before retaining percentages -> hedged descriptive | verified |
| C03 | Symmetric-LR control is claimed to separate calibration from update asymmetry. | evidence/scope_C02_C03.md | no paired control, hedged to mechanism not identified | Require seed-level symmetric-LR outputs and predefined test -> hedged | verified |
| C04 | The mechanism of any partial mitigation (bias reduction vs output smoothing) is not identified. | evidence/scope_C04_C05.md | not identified, hedged to rank-preserving future work | Add rank-preserving/negative-control mechanism experiment -> hedged | verified |
| C05 | Relationship to the calibration-noise result in P15 is not discussed in the current manuscript. | evidence/scope_C04_C05.md | not discussed, hedged to cross-paper future work | Add cross-paper reconciliation and shared metric definitions -> hedged | verified |
| C06 | Canonical source uses anonymous TMLR form. | main.tex | anonymous | Scoped TMLR scan | verified |

## Strong-claim audit

The 20–49% and 45–67% headline effects are not promoted without the missing per-seed result archive. Existing review recommendation is Major Revisions.
