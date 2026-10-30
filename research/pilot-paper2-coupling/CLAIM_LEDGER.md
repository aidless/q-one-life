# Paper 2 evidence-qualified claim ledger

Canonical upstream: `evidence/upstream/paper/main.tex`

Canonical SHA-256: `379e1632302e979ded0c0462eeba32a07fa82653796ca72d4f9f55e46f8d5cec`

Overlay source: `source/main.tex`

Overlay SHA-256 is checked by `project.json`; the upstream bytes remain
unchanged. This ledger normalizes the native `P2-C1..P2-C14` IDs into the
six-column verifier format without changing the original ledger copied under
`evidence/upstream/source/CLAIM_LEDGER.md`.

| ID | Claim | Evidence file + field | Numeric values | Verification | Status |
|---|---|---|---|---|---|
| C01 | Six standalone theory TeX files and six experiment JSON outputs encode the theorem program; T3 and T4 are preserved inside T5 rather than separate files | `evidence/native-audit.json` -> counts.theory_tex_files / counts.experiment_json_files / counts.native_claims | 6 / 6 / 14 | Inventory only; independent proof audit remains absent | candidate |
| C02 | The favorable-region emptiness is descriptive of the 11-condition reconstruction and is not a universal impossibility result | `evidence/native-audit.json` -> counts.scope_heldout_mentions / counts.heldout_data_files | 9 / 0 | Scope docs mention held-out work; no held-out data receipt exists | candidate |
| C03 | The reported tight-bound improvement is sample-descriptive rather than an independent held-out validation | `evidence/upstream/source/evidence/scope_P2C3.md`; `evidence/native-audit.json` -> checks.heldout_data_file_present | 0 | Held-out validation remains future work | candidate |
| C04 | The Pinsker analysis is outside its small-gamma regime for the observed grid | `evidence/upstream/source/experiments/T1_pinsker_fit.json` -> n_in_small_gamma_regime / n_conditions | 0 / 11 | No small-gamma cells in the delivered sample | candidate |
| C05 | The logistic Cramer-Rao bound is not automatically equivalent to the measured weight-distance coupling estimator | `evidence/upstream/source/evidence/scope_P2C5.md`; `evidence/upstream/source/experiments/T2_multiparameter.json` -> n_gamma_obs | 65 | Estimand mapping remains conditional and requires independent audit | candidate |
| C06 | The product-bound inequality is only available after replacing the original entropy upper-bound direction with an assumed entropy floor | `evidence/upstream/source/evidence/scope_P2C6.md`; `evidence/upstream/source/theory/T5_minimax.tex` | - | Proof audit remains open | candidate |
| C07 | T5 and T8 report consistent outputs, while T6 reports an empirical bound below its claimed bound | `evidence/upstream/source/experiments/T6_ensemble_K4.json` -> empirical_gamma_H_CV_K4 / bound_at_K4_delta_0.05 | 0.063247 / 0.384555 | The T6 discrepancy is preserved rather than relabeled as consistency | candidate |
| C08 | The four-axis polytope remains descriptive; the native scope text and the frozen T7 output do not yet agree on the satisfied-cell count | `evidence/upstream/source/evidence/scope_P2C8.md`; `evidence/upstream/source/experiments/T7_polytope.json` -> n_all_constraints_satisfied / n_cells_tested | 0 / 20 | Requires estimator and constraint reconciliation | candidate |
| C09 | CV values at different N and estimator definitions are not pooled into a direct comparison | `evidence/upstream/source/evidence/scope_P2C9.md`; `evidence/upstream/source/experiments/T2_multiparameter.json` -> N_samples | 30 | Scope-limited; pooled estimand not claimed | candidate |
| C10 | Standard psychometric baselines such as kappa, ICC and Rasch are outside the current comparison scope | `evidence/upstream/source/evidence/scope_P2C10.md` | - | Scope limitation remains explicit | candidate |
| C11 | GPT-4o drift is not robust at N=8, and the native p=0.12 statement conflicts with the frozen p_bootstrap=1.0 artifact | `evidence/upstream/source/evidence/scope_P2C11.md`; `evidence/upstream/source/evidence/analyses/gpt4o_drift_june_snapshot.json` -> n_seeds; `evidence/upstream/source/evidence/analyses/mm_epc_gpt4o_replication.json` -> p_bootstrap | 8 / 1.0 | Native p=0.12 is not recomputable from the frozen JSON; blocked | blocked |
| C12 | All eleven condition rows are represented in the decision-case table and the 66 table numbers are preserved in the frozen carrier index | `evidence/native-audit.json` -> counts.bound_decision_rows / counts.table_numbers | 11 / 66 | Traceability passes; this does not prove correctness | verified |
| C13 | The current reproducibility bundle is incomplete because it lacks held-out data, a complete environment lock and a public release receipt | `evidence/native-audit.json` -> counts.carrier_receipts_passed / counts.heldout_data_files / counts.proof_audit_receipts | 176 / 0 / 0 | Numerical carriers pass; missing gates remain explicit | candidate |
| C14 | Adversarial review is not closed: the frozen review summary still records five Major issues and the meta-review recommends Major Revisions | `evidence/upstream/source/review_real/summary.json` -> r6.major / r6.critical; `evidence/native-audit.json` -> checks.meta_review_reports_major_revisions | 5 / 0 | Independent closure is absent; blocked | blocked |

`candidate` means the evidence supports only a qualified statement.
`blocked` means the current claim must not be promoted into readiness language.
Only C12 is verified, and only at the artifact-traceability level.
