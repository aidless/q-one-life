# Claim ledger — closing_landscape

| ID | 声明 | 证据文件+字段 | 数值 | 如何验证 | 状态 |
|---|---|---|---|---|---|
| C01 | The archived joint experiment records 15 seeds in the simulation aggregate, with standard, CG, and CG+TEE aggregate gamma/CV values. | evidence/cg_tee_results.json -> config.n_seeds / aggregate.standard.gamma_mean / aggregate.cg_alone.gamma_mean / aggregate.cg_tee.gamma_mean | 15 / 0.1429878956 / 0.7187781642 / 0.5740180983 | Recompute aggregate from per-seed archive and preserve artifact identity | verified |
| C02 | The final-results artifact reports a different standard/CG/TEE triplet than the joint aggregate. | evidence/cg_tee_final_results.json -> uncalibrated[0].gTV / calibrated[0].gTV / cg_tee[0].gTV | 1.0111 / 0.6196 / 0.6850 | Compare seed-level schema and provenance before choosing a canonical result | verified |
| C03 | The real-API artifact has CG and CG+TEE gamma=0 and H=1 for every completed seed, indicating confidence-parser fallback/degeneracy rather than the claimed effect. | evidence/cg_tee_real_results.json -> results[0].cg_alone.gamma_TV / results[0].cg_alone.H_T | 0 / 1 | Inspect all 15 seeds and parser logs; do not treat as successful mitigation | verified |
| C04 | The manuscript headline values (0.991→0.602→0.644; CV 0.177→0.159) cannot be uniquely traced to one internally consistent artifact. | evidence/cg_tee_final_results.json | conflicting sources (cross-check: `cg_tee_real_results.json`) | Require a rerun or provenance reconciliation before retaining headline claims | blocked |
| C05 | The favorable-regime hypothesis is not falsified by the archived aggregate; no joint result currently establishes Strong Accept evidence. | evidence/cg_tee_results.json -> hypothesis_test.favorable_regime_occupied / hypothesis_test.calibration_tradeoff_falsified | false / false | Keep as null result pending valid real-API rerun | inconclusive |
| C06 | Canonical source uses anonymous TMLR form. | main.tex | anonymous | Scoped TMLR scan | verified |

## Strong-claim audit

The existing readiness diagnosis is a soundness blocker: the claimed CG/TEE numbers are not reproducible from a single provenance chain, and the real run degenerates to zero coupling. No headline mitigation claim may be promoted.
