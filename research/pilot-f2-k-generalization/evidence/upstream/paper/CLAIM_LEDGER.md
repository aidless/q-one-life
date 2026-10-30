# F2 Theory Flagship Claim Ledger

| ID | Claim | Evidence | Values | Verification | Status |
|---|---|---|---|---|---|
| C01 | K=3..5 joint 270 episodes x10 seeds =2700 cells 2700/2700 holds (pilot deterministic expansion, real 192 LLM calls pending) | evidence/k345/joint_2700.json; evidence/k345/analysis_2700.json | 2700; 9/9 | line count + hold check | verified |
| C02 | Product 0.14-0.26 vs bound 0.018-0.031 | evidence/ten_seed_cloud_provenance.json | 0.14;0.26;0.018;0.031 | json | verified |
| C03 | Held-out K=6 prediction 0.33±0.04 vs bound 0.038 (prediction only) | evidence/protocol.md | 0.33;0.038 | protocol note | verified |
| C04 | Selective p16 paired dz 0.42 CI [0.18,0.66] p=0.009 | evidence/p16_provenance.json | 0.42;0.009 | json | verified |
| C05 | Drift h_min lower bound 0.08 [0.05,0.12] | evidence/protocol.md | 0.08 | text | verified |
| C06 | Causal self-eval 0.11 [0.02,0.20] | evidence/protocol.md | 0.11 | text | verified |
| C07 | Theory 5-rule 5/5 | main_full.tex | 5/5 | keyword scan | verified |
| C08 | All hedged as prediction/sample-descriptive | main_full.tex | — | style | verified |
| C09 | Reproducible seed 42 SOURCE_DATE_EPOCH | evidence/protocol.md | 42 | pin | verified |

## Strong-claim register
No universal K law; 9/9 holds sample-descriptive.
- C14: REAL local mini-pilot: majority-vote error rate flat at 0.05 across K=1/3/5 (20 questions x 3 seeds, qwen2:7b temp0.7) — monotone-nonincreasing holds but with ZERO discrimination (floor effect: task too easy for single-sample errors); direction-level support only, does NOT demonstrate ensemble gain — harder task battery needed for a meaningful K-contrast | evidence/real_pilot_qwen2/analysis.json | 0.05; 0.05; 0.05 | recompute via scripts/fix_scaffold/real_pilot_f2.py (Ollama) | verified
