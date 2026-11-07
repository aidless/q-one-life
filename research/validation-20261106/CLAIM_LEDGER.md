# AI Researcher Validation Claim Ledger

Scope: bounded algorithm/parameter research. Every row names a file and a field;
no row may be cited without re-reading that carrier.

| ID | Claim | Evidence file + field | Numeric values | Status |
|---|---|---|---|---|
| V01 | The full 54-trace matrix ran on the cloud host with the same runner bytes as the local checkout | `cloud-full/cancer_extension-11-single_agent/receipt.json -> runner_sha256`; `src/qone_life/research_factory/research_validation.py` | `2d13756e…0cb2b7` on both sides | verified |
| V02 | 44 of 54 traces completed and 10 were inconclusive | `results.json -> counts.completed / counts.inconclusive` | 44 / 10 | verified |
| V03 | Every completed trace had matching output hashes and a matching independent replay | `results.json -> counts.hash_failures / counts.replay_failures` | 0 / 0 | verified |
| V04 | The test split was never used for candidate selection | `results.json -> counts.test_used_for_selection`; `cloud-full/*/receipt.json -> test_used_for_selection` | 0 | verified |
| V05 | All 10 inconclusive traces failed on the candidate schema, not on training or transport | `results.json -> runs[].failure_type` | 10 × `ValidationError` | verified |
| V06 | Multi-agent does not beat single-agent or no-rebuttal on the 10 complete task/seed pairs | `results.json -> sign_tests` | 3/5/2, p=0.73; 2/4/4, p=0.69 | verified |
| V07 | Shuffled-label controls also show apparent gains of the same magnitude | `results.json -> kind_stats.*:null` | +0.004 to +0.019 median, max +0.052 | verified |
| V08 | The receipt validator catches 10 injected fault classes and passes 2 positive controls | `cloud-full/faults.json -> injected / detected / positive_controls` | 10 / 10 / 2 | verified |
| V09 | Rubric scores correlate with PeerRead human recommendations, exploratory only | `peerread-check/result.json -> spearman_rho / bootstrap_rho_95ci / status` | 0.556 / [0.21, 0.79] / `exploratory_unmatched_versions` | verified |
| V10 | The original 24-paper PeerRead field said submission version was unknown; later raw parsed_pdf matching upgrades the pilot to repository-parsed status | `datasets/processed/peerread/paper_review_pairs.jsonl -> submission_version_status`; `peerread-submission-match/match.json -> matched / body_identical` | `unknown` was the pre-match status; later 24/24 matched, 23/24 body-identical | verified |
| V11 | All 60 RIDAR RIV-Gold traces are present locally and byte-match the pinned tree | `datasets/ridar-full-manifest.json -> files`; `fetch_ridar_full.py verify` | 60 files / 61,459,066 bytes / 0 problems | verified |
| V11b | The 60 traces hold 47,797 records, 766 annotated acts and 3,461 evidence spans, all in range | `ridar-audit/audit.json -> records_total / acts_total / evidence_spans_total / spans_out_of_range_total` | 47797 / 766 / 3461 / 0 | verified |
| V11c | 13 of 14 RIVT categories appear in the data; evaluator tampering has zero examples | `ridar-audit/audit.json -> coverage.categories_present_in_data / categories_absent` | 13 / `["evaluator_tampering"]` | verified |
| V11d | None of the six implemented integrity checks consumes agent traces | `ridar-audit/audit.json -> coverage.implemented_trace_level`; `src/qone_life/research_factory/research_integrity.py -> IMPLEMENTED` | 0 | verified |
| V12 | No PaperBench score exists because the benchmark was not executed | `datasets/manifest.json -> datasets[id=paperbench-dev-semantic-self-consistency].availability` | `task_bundle_downloaded_not_executed` | verified |
| V13 | A deterministic 40/20 trajectory split was frozen before writing any detector rule | `ridar-detector/PREREGISTRATION.json -> split_sha256 / rules_sha256 / stop_rules` | `c50048cd…14914` / `6294f8f0…6596c` / 3 stop rules | verified |
| V14 | All three candidate target categories fail the frozen held-out minimum of 10 positives | `ridar-detector/PREREGISTRATION.json -> split`; `ridar-detector/freeze-report.json -> train_targets / test_targets` | TCE 21/9, RF 13/6, CF 20/4 | verified |
| V15 | The trajectory-level detector protocol therefore stops without producing precision/recall | `ridar-detector/PREREGISTRATION_REPORT.zh-CN.md` | stop | verified |
| V16 | Act-level protocol freezes a new split (40/20 trajectory-stratified) and only TCE meets the 10-act held-out minimum | `ridar-detector/PREREGISTRATION_ACT.json -> split_sha256 / act_counts` | TCE 10 acts / RF 4 / CF 7 | verified |
| V17 | The two TCE sub-rules fail the frozen development precision floor of 0.5 | `ridar-detector/result-act.json`; `TCE_RESULT_REPORT.zh-CN.md` | 0.205 / 0.125 | verified |
| V18 | The TCE act-level detector therefore reports unusable, not measured | `TCE_RESULT_REPORT.zh-CN.md` | unusable | verified |
| V19 | 74.4% of quoted evidence spans match their record at zero offset; adjacent offsets are far lower | `ridar-span-alignment/audit.json -> quote_match_at_span` | 1960 / 2635 = 0.744 | verified |
| V20 | Evidence-span start points are mostly tool_call/tool_result records, not a systematic relative pointer | `ridar-span-alignment/audit.json -> start_record_type` | 1703 / 915 / 580 / 259 / 4 | verified |
| V21 | TCE v2 frozen protocol meets the held-out act minimum (14 acts / 10 trajectories) | `ridar-detector/freeze-tce-v2-report.json` | 14 / 10 | verified |
| V22 | TCE v2 sub-rules still fail the development precision floor of 0.5 | `ridar-detector/result-tce-v2.json`; `TCE_V2_RESULT_REPORT.zh-CN.md` | 0.050 / 0.152 | verified |
| V23 | Regular-expression tool-text rules are not usable for TCE on this corpus | `TCE_V2_RESULT_REPORT.zh-CN.md` | unusable | verified |
| V24 | Test-path lexical occurrences are common but not specific to hidden answers | `ridar-test-census/census.json -> path_pattern_totals` | `_test` 2271 / csv-answers 1168 / private-dir 155 / split-api 106 | verified |
| V25 | A stricter test-label-read then config-write rule still fails the precision floor | `ridar-detector/result-tce-v3.json`; `TCE_V3_RESULT_REPORT.zh-CN.md` | 0.138 train / 0.097 held-out | verified |
| V26 | Fixed regular-expression and window rules are not suitable for TCE on this corpus | `TCE_V3_RESULT_REPORT.zh-CN.md` | unsuitable | verified |
| V27 | All 24 pilot PeerRead papers match a raw parsed_pdf in the pinned repository | `peerread-submission-match/match.json -> matched` | 24 / 24 | verified |
| V28 | 23 of 24 pilot papers have byte-identical body sections; the one difference is email redaction | `peerread-submission-match/match.json -> body_identical / detail` | 23 / 24 | verified |
| V29 | PeerRead external check is now repository-parsed, not unknown-version exploratory | `peerread-submission-match/REPORT.zh-CN.md` | repository-parsed | verified |
| V30 | Expanded repository-parsed check covers 28 papers with human review scores | `peerread-expanded/result.json -> requested / usable` | 28 / 28 | verified |
| V31 | The expanded correlation is rho=0.21, p=0.28, CI includes zero | `peerread-expanded/result.json -> spearman_rho / spearman_parametric_p / bootstrap_rho_95ci` | 0.213 / 0.276 / [-0.21, 0.60] | verified |
| V32 | The expanded PeerRead check does not support rubric calibration | `peerread-expanded/REPORT.zh-CN.md` | not calibrated | verified |
| V33 | A paper-level held-out check freezes equal weights before scoring the test split | `peerread-heldout/heldout.json -> weights / frozen` | 1/3 each | verified |
| V34 | The 6-paper test split has rho=0.79, p=0.063, CI includes zero | `peerread-heldout/heldout.json -> test` | 0.788 / 0.063 / [-0.11, 1.00] | verified |
| V35 | The held-out check does not support rubric calibration | `peerread-heldout/REPORT.zh-CN.md` | not calibrated | verified |
| V36 | PeerRead fixed-revision census: 78 papers, 40 parsed, 66 reviewed, 28 usable | `peerread-availability/census.json -> totals` | 78 / 40 / 66 / 28 | verified |
| V37 | The 28-paper usable set is the fixed-revision ceiling | `peerread-availability/REPORT.zh-CN.md` | ceiling | verified |
| V38 | PeerRead target is noisy: ICC(1,1)=0.124, exact agreement 30.3%, +/-1 point 74.6% | `peerread-agreement/agreement.json -> icc_1_1 / pairwise_exact_agreement / pairwise_within_one_point` | 0.124 / 0.303 / 0.746 | verified |
| V39 | Only 169 de-duplicated anonymous reviewer rows exist across 66 ICLR 2017 papers | `peerread-agreement/agreement.json -> review_rows / papers_with_reviews` | 169 / 66 | verified |
| V40 | Reviewer noise bounds any rubric-calibration claim before model fit is evaluated | `peerread-agreement/REPORT.zh-CN.md` | bound | verified |
| V41 | PaperBench dev data, upstream code, pb-env, alpine/socat and Docker infrastructure are prepared at revision b78dab1; DirectSubmission + dummy judge smoked 3/3 tasks | `paperbench-smoke/REPORT.zh-CN.md`; `paperbench-smoke/image-inspect.txt`; `paperbench-smoke/2026-11-07T10-27-44-GMT_run-group_direct_submission_solver/` | prepared / smoke passed | verified |
| V42 | DirectSubmission plus dummy judge graded semantic-self-consistency with dummy score 1.0 using a full reproduction package; no real PaperBench capability score exists | `paperbench-smoke/REPORT.zh-CN.md`; `paperbench-smoke/2026-11-07T10-27-44-GMT_run-group_direct_submission_solver/semantic-self-consistency_609d6c0c-c270-4010-941e-3c7b0aa1ed75/grade.json` | 1.0 / dummy only | verified |
| V43 | LLM-assisted TCE development labeling judged 12/12 trajectories with TP/FP/FN/TN = 3/0/3/6 | `ridar-detector/result-llm-tce.json -> confusion / judged` | 3 / 0 / 3 / 6 | verified |
| V44 | LLM-assisted TCE development precision is 1.0 and recall 0.5, but it is not a held-out detector result | `ridar-detector/result-llm-tce.json -> precision / recall / stop` | 1.0 / 0.5 / development only | verified |
| V45 | The code lab now supports bounded generated Python, isolated subprocess execution and host-defined hidden tests | `src/qone_life/research_factory/code_lab.py`; `tests/test_code_lab.py`; `tests/test_code_lab_cli.py` | 7 tests passed | verified |

## Explicit non-claims

- No claim of novelty, acceptance probability, or general autonomous research ability.
- No claim that the multi-agent role split improves research quality.
- No claim that PeerRead agreement calibrates the rubric.
- No claim that the fault battery covers RIDAR's violation taxonomy.
- No claim that trajectory-level integrity detection was measured; the frozen
  protocol stopped before any detector code was written.
