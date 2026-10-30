# Benchmark Noise Floor Claim Ledger

Manuscript: `source/main.tex`
Current source SHA-256: `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca`
Native manifest source SHA-256: `0d68bda378fa0fc4fe1d39c8c8d46ba39052230fae7a1e8f2fd44b41e5b7e113`

This Q-One overlay summarizes a much larger native evidence ledger. The copied
native ledger contains 569 entries; the adapter verifies source fields and
values without rewriting the paper or claiming that named derivations were run.

| ID | Claim | Evidence file + field | Numeric values | Verification | Status |
|---|---|---|---|---|---|
| C01 | The native ledger has 569 entries, of which 472 resolve to matching source fields, 78 use named derivations, 8 use written field waivers, 8 are unbound registers, and 3 are explicitly unrecoverable retractions. | `reports/native-ledger-audit.json -> counts.entries_total / counts.field_verified / counts.named_derivation / counts.field_waiver / counts.unbound_register / counts.unrecoverable_retraction` | 569 / 472 / 78 / 8 / 8 / 3 | Re-run `research-native-ledger` against the copied native ledger and original workspace root | verified |
| C02 | The current `source/main.tex` is byte-identical to the source recorded in the native manifest. | `evidence/native-manifest.json -> paper.main.tex.sha256` | - | Compare the manifest source hash with the current source; mismatch blocks publication identity | blocked |
| C03 | The producer-baseline construction measures leaderboard readability rather than only agreement with the gold producers. | `evidence/REVIEW_INDEPENDENT_2026-10-24.md` | - | Resolve the independent review's A1 construct-validity objection or narrow the paper's claim | blocked |
| C04 | A real public leaderboard with a gold pool disjoint from the ranked systems has produced a READABLE verdict. | `evidence/REVIEW_INDEPENDENT_2026-10-24.md` | - | Run the ruler on a suitable external leaderboard and preserve the result | candidate |
| C05 | The current source copy passes the mechanical LaTeX package audit. | `reports/package-audit.json -> mechanical_pass / blockers` | - | Re-run `research-package-check`; this does not establish scientific readiness | verified |
| C06 | Three native numeric gates pass twice against the current source bytes: 250/250 manuscript numbers, 353 reverse-coverage reads with 0 unbound, and an anchor census with A1=0. | `reports/native-numeric-gate.json -> state / source.sha256 / checks.numbers / checks.reverse / checks.anchor` | 250 / 250 / 353 / 0 / 0 | Re-run `tools/run_native_numeric_gates.py`; compare both run hashes and the source hash before/after | verified |
| C07 | The current source tree compiles twice in isolated directories to a byte-identical 45-page PDF. | `reports/cleanroom/receipt.json -> exit_codes / pdf.pages / pdf.deterministic / source.main_sha256` | 45 | Re-run `scripts/cleanroom_compile.py` against the overlay source; this does not establish scientific readiness | verified |
| C08 | The eleven-file source builds a deterministic candidate archive, and extracting that archive compiles to a 45-page PDF. | `reports/package/package-receipt.json -> source.file_count / archive.deterministic / extract_compile.exit_code / extract_compile.pdf_pages` | 11 / 0 / 45 | Rebuild the archive and compare both hashes; extract and compile separately | verified |
| C09 | In a frozen synthetic construction, three perfect producers set the leave-one-out floor at 1.0; systems A and B score 0.9 and 0.5; A remains above B under all 700 single-item deletions with 280 A-only and 0 B-only paired observations; the declared gate still refuses. The positive and negative controls also match, and two accepted runs are byte-identical. | `experiments/producer-baseline-counterexample/results/reproduction.json -> hypothesis_decision / condition_summary[0].producer_floor / condition_summary[0].system_accuracies.A / condition_summary[0].system_accuracies.B / condition_summary[0].paired_discordance.first_only_correct / condition_summary[0].paired_discordance.second_only_correct / condition_summary[0].single_item_deletions_stable / condition_summary[1].gate_readable / condition_summary[2].observed_relation / byte_identical` | 1.0 / 0.9 / 0.5 / 280 / 0 / 700 / true | Re-run `run_counterexample.py` twice and compare all preselected signatures and output hashes | verified |
| C10 | Git commit `9eb77f1b77baaa9932d8faf18da2fc50a2077f6c` recovers the source blob named by the native manifest at SHA-256 `0d68...e113`; the current source differs by 8 added and 5 removed lines, so source lineage is valid but publication identity is not established. | `evidence/source-lineage.json -> state / lineage_valid / recovered.sha256 / diff.added_lines / diff.removed_lines / publication_identity_ready` | recovered_revision / true / 8 / 5 / false | Re-run `audit_git_source_lineage` against the recorded commit and compare both source hashes | verified |

| C11 | On the four $m=25$ carriers the reselected-leader margin `max_s acc(s) - max_g LOO(g)` is exactly zero in every one of 2000 case-cluster bootstrap rounds, while the printed fixed-winner interval reproduces the recorded native intervals and is never positive in any round; two controls with a broken hypothesis move the same statistic to a strictly positive and a strictly negative interval. | `experiments/bootstrap-estimand-a2/results/run-1.json -> status / tasks.factuality.theta_both_interval.n_zero_rounds / tasks.factuality.theta_fixed_interval.lo95 / tasks.coherence.theta_fixed_interval.lo95 / tasks.relevance.theta_fixed_interval.lo95 / tasks.preference.theta_fixed_interval.lo95 / controls.nonproducer_leader.theta_both_interval.lo95 / controls.nonproducer_leader.theta_both_interval.hi95 / controls.unranked_generator.theta_both_interval.lo95 / controls.unranked_generator.theta_both_interval.hi95` | completed / 2000 / -3.9018 / 0.0 / -0.7071 / -1.7309 / 3.2720 / 7.3469 / -2.6750 / 0.0 | Re-run `run_estimand_split.py` twice against the pinned preregistration and compare all gates plus the byte-identical output hashes; the controls are experiment-internal constructions, not leaderboard measurements | verified |
| C12 | On the four fixed m25 carriers, the recorded leaky LOO-on-k-fold-domain margins reproduce, but on the joint main-gold, LOO-gold, fold-gold and actor support all four LOO margins are exactly zero; the k-fold margins remain 0.0 / 2.872063 / 0.616016 / 1.851852, every checked LOO label equals the full gold label, and two runs are byte-identical. The joint supports are 477 / 383 / 974 / 54, so the 54-item preference result is descriptive only. | `experiments/kfold-common-support-a3/results/reproduction.json -> byte_identical / task_summary.factuality.joint_domain / task_summary.coherence.reported_leaky_loo_margin / task_summary.coherence.kfold_reported_domain / task_summary.coherence.joint_domain / task_summary.relevance.joint_domain / task_summary.preference.joint_domain / task_summary.factuality.loo_joint_margin / task_summary.coherence.loo_joint_margin / task_summary.relevance.loo_joint_margin / task_summary.preference.loo_joint_margin / task_summary.factuality.kfold_joint_margin / task_summary.coherence.kfold_joint_margin / task_summary.relevance.kfold_joint_margin / task_summary.preference.kfold_joint_margin / task_summary.factuality.label_mismatches / task_summary.coherence.label_mismatches / task_summary.relevance.label_mismatches / task_summary.preference.label_mismatches` | true / 477 / 0.471116 / 404 / 383 / 974 / 54 / 0.0 / 0.0 / 0.0 / 0.0 / 0.0 / 2.872063 / 0.616016 / 1.851852 / 0 / 0 / 0 / 0 | Re-run the frozen A3 protocol twice and compare hashes plus all five gates; the k-fold control and support sizes limit the interpretation | verified |
| C13 | The pinned native CLI has no delta parameter: help omits `--delta`, invoking it exits 2, and the source hard-codes the 2.0-point decision branch. A synthetic fixture with derived raw margin 2.0000000000000018 is rounded to 2.0 and classified READABLE, while the R2 candidate instructs a reader to treat equality as MARGINAL. A different fixture has point margin 13.6364 and 95% interval [-100.0, 21.124], yet remains READABLE. Domain-mismatch, two-generator floor and no-reading controls still return refusals, and two accepted runs are byte-identical. | `experiments/threshold-interface-a4/results/reproduction.json -> byte_identical / gates.F1_threshold_is_not_a_cli_parameter.passed / gates.F1_threshold_is_not_a_cli_parameter.evidence.delta_invocation_exit_code / gates.F2_equality_branch_mismatch_reproduced.derived_raw_margin_points / gates.F2_equality_branch_mismatch_reproduced.json_margin_points / gates.F2_equality_branch_mismatch_reproduced.implementation_verdict / gates.F4_confidence_interval_is_not_gating.margin_points / gates.F4_confidence_interval_is_not_gating.margin_ci.lo95 / gates.F4_confidence_interval_is_not_gating.margin_ci.hi95 / gates.F4_confidence_interval_is_not_gating.verdict / gates.F5_fail_closed_controls.passed` | true / 2 / 2.0000000000000018 / 2.0 / 13.6364 / -100.0 / 21.124 | Re-run the frozen A4 protocol twice and compare hashes plus all five gates; these are synthetic interface fixtures, not external leaderboard measurements | verified |
| C14 | Revision candidate R3 binds the unmodified canonical source, parent candidate R2, A3/A4 evidence and candidate-specific overlays. Its source compiles twice to the same 46-page PDF, the package audit passes for 11 files, reverse coverage reads 355 tokens with 352 bound, 3 excused and 0 unbound, the anchor census is GREEN with 0 missing anchors, and the verdict-word gate passes 137/137. These facts establish candidate-level mechanical integrity only. | `revisions/2026-10-29-support-threshold-r3/reports/cleanroom/receipt.json -> pdf.pages / pdf.deterministic / pdf.sha256_run1 / pdf.sha256_run2`; `revisions/2026-10-29-support-threshold-r3/reports/candidate-gates-summary.json -> status / reverse_coverage.n_tokens / reverse_coverage.n_bound / reverse_coverage.n_excused / reverse_coverage.n_unbound / anchor_census.verdict / anchor_census.anchor_missing / verdict_word_gate.checks / verdict_word_gate.failures` | 46 / true / 355 / 352 / 3 / 0 / GREEN / 0 / 137 / 0 | Verify `revisions/2026-10-29-support-threshold-r3/SHA256SUMS.txt`, then rerun only through `run_candidate_gates.py` if a new receipt generation is intended; compilation and gate passage do not close C02/C03 or establish scientific readiness | verified |

## Aggregate evidence

The copied native files are:

- `evidence/native-paper-ledger.json`
- `evidence/native-manifest.json`
- `evidence/verdict-claims.json`
- `evidence/native-ledger-pointer.json`
- `evidence/REVIEW_LOCAL_2026-10-24.md`
- `evidence/REVIEW_INDEPENDENT_2026-10-24.md`

The adapter deliberately leaves 78 named derivations as `candidate`; it does not
execute formulas without their original code and environment.

The C09 counterexample is a synthetic logical witness, not an external
leaderboard study. It rejects the broad claim that producer-baseline clearance
is necessary for every resolvable top ordering. It does not close the open
independent review or establish publication readiness. Three failed
preregistration attempts are preserved under
`experiments/producer-baseline-counterexample/attempts/` and are not accepted
as evidence.

## Revision candidate R1

`revisions/2026-10-28-construct-validity-r1/` is a separate wording revision,
not the canonical manuscript. It removes the mistaken necessity reading of
producer-baseline clearance while preserving the reported calibrated arm and
the disjoint-field deployment. Its two-run compile is deterministic at 45
pages; the candidate-specific reverse-coverage gate reports 353 readings with
0 unbound, and the verdict-word gate passes 136/136 checks. C03 remains
`blocked`: the independent method review is open, and this candidate does not
settle review findings A2 (bootstrap estimand), A3 (k-fold common support), or
A4 (threshold and interface semantics).

## A2 estimand split

`experiments/bootstrap-estimand-a2/` separates two statistics that share inputs
but not targets. `theta_fixed` freezes the point-estimate winner and
re-maximises the floor inside every round; `theta_both` re-selects the leader as
well. On the four `m=25` carriers `theta_both` is exactly zero in 2000 of 2000
rounds, so the Proposition 4 identity has a degenerate interval rather than an
unprinted one, and the printed interval belongs to `theta_fixed` alone. The two
controls (a leader that is not a generator; a generator that is not ranked) show
that the `[0, 0]` outcome is not automatic. A2 is closed as a wording and
labelling question; A3 and A4 remain open in the independent review.

## A3 k-fold common support

`experiments/kfold-common-support-a3/` tests the support leak named by the
independent review. The native k-fold domain requires the fold gold and main
gold, but not every generator's own LOO gold; the leaky LOO arm then drops
undefined LOO items separately for each generator. On the joint support formed
from the main gold, every LOO gold, every fold gold and every generator/system
answer row, the LOO margin is exactly zero on all four tasks and the bootstrap
identity is zero in 2000/2000 rounds. The 47,200 checked generator/item label
pairs contain 0 mismatches. A coherence k-fold control remains positive
(`+2.872063 [1.308815, 4.545455]`), so the zero LOO result is not produced by
forcing all arms to zero.

This answers A3's support question but does not make the k-fold comparison a
ranking-validity result. The joint supports are 477/383/974/54 items; preference
shrinks to 54 because the ranked systems do not share a larger answer domain.
The manuscript still needs an explicit support definition and a corrected
comparison. At the end of A3, C02/C03 remained `blocked`, A4 remained open, and
no upload was authorized.

## Revision candidate R2

`revisions/2026-10-29-estimand-split-r2/` is an internal candidate built on R1,
not the canonical manuscript. It replaces R1's underspecified identity sentence
with the shared-domain deduction and corrects the falsified coherence sentence:
8 of 2000 accepted A2 rounds separate the re-maximised floor from the fixed
leader, but that count lies below the 2.5% tail, so the interval still collapses
to `[0, 0]`. The candidate compiles twice to a byte-identical 45-page PDF,
passes the mechanical package audit, reads 353 manuscript numbers with 0
unbound, passes 136/136 verdict-word checks, and has a GREEN anchor census.
These gates bind the candidate but do not make it scientifically ready. C02
and C03 remain `blocked`; R2 was built before A3 and A4 evidence were integrated
and therefore still records A3 (k-fold common support) and A4 (threshold and
interface semantics) as open. R2 does not overwrite `source/main.tex`, does not
close the independent review, and does not authorize an arXiv upload.

## A4 threshold and interface semantics

`experiments/threshold-interface-a4/` executes seven deterministic fixtures
against the pinned native `audit.py`. The CLI exposes no `--delta` option:
`--help` omits it, invoking it exits 2 as an unrecognized argument, and the
pinned source contains the hard-coded 2.0-point branch and metadata literal.

The equality fixture derives a raw margin of `2.0000000000000018`, which the
native JSON rounds to `2.0`; the tool returns `READABLE`, while the R2 candidate
tells a reader that equality should be treated as `MARGINAL`. The branch is
`margin < delta`, so an exact `2.0` also takes the readable arm. A separate
fixture has point margin `13.6364` and a 95% case-bootstrap interval
`[-100.0, 21.124]`, but the verdict remains `READABLE`: the interval is printed
after the branch and does not gate it. Domain mismatch, two-generator floor
degeneracy and unresolved-gold controls continue to return refusals.

This answers the A4 threshold/CLI/equality/CI sub-questions at the interface
level. It does not resolve the review's MDE terminology or generator
independence objections, does not show ranking validity, and does not close
C02/C03. R3 must replace the duplicate competing R2 equality sentences with
one executable policy and may not describe an interval-gated rule until the
implementation and manuscript agree.

## Revision candidate R3

`revisions/2026-10-29-support-threshold-r3/` is an internal candidate built on
R2. Its source SHA-256 is `a9eef802...e0bb6`; it replaces the competing equality
instructions with `leader - floor >= delta`, records `delta = 2.0` as a
hard-coded implementation constant, states that the confidence interval is
printed but does not gate the verdict, and replaces the mixed-support k-fold
comparison with the A3 joint-support result. The 54-item preference support is
descriptive only.

The 35-file hash inventory excludes only itself and verifies together with the
manifest. The candidate compiles twice to a byte-identical 46-page PDF, passes
the 11-file package audit, reads 355 numeric tokens with 352 bound, 3 excused
and 0 unbound, has a GREEN anchor census with 0 missing anchors, and passes
137/137 verdict-word checks. These receipts bind this candidate source; they do
not make it the canonical manuscript, do not close C02/C03, and do not
establish scientific readiness or upload authorization. The independent
review's MDE terminology and generator-independence objections remain open,
and no real disjoint-field leaderboard with a positive verdict has been
measured.

`REVIEW_REQUEST_R3.md` freezes a read-only review packet that maps every
original A1-A4 finding to R3 evidence and asks the reviewer to decide whether
the remaining block is a textual revision or an external evidence requirement.
The packet has not been sent; no independent review of R3 exists yet.
