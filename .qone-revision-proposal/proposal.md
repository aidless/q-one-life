# Noise Floor Revision Proposal — Construct-Validity Audit Version

**Generated at**: 2026-10-28T13:45Z  
**Evidence gate**: `research/pilot-bench-noise-floor/experiments/producer-baseline-counterexample/results/reproduction.json`  
**Counterexample hash**: `fa0846484b4dba64236caf2aeefb2b70d3db8f6bab78b5ad1fe6067f289cd424` (`reject_H0_in_declared_synthetic_condition`)  
**Source identity**: `0d68bda378fa0fc4fe1d39c8c8d46ba39052230fae7a1e8f2fd44b41e5b7e113` recovered from commit `9eb77f1b77baaa9932d8faf18da2fc50a2077f6c`; manuscript is current revision `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca`, lineage_valid=true, publication_identity_ready=false

## What must change in the paper

- **Abstract** lines 76–81: Remove "the leader is readable only if it clears that floor" and "public ranking is readable" assertions. Replace with statement that tool measures "when consensus-gold constructions fail to yield a verdict, and how design choices determine that outcome."

- **Introduction** §1(97–99): Delete "A readable verdict is therefore a necessary condition for citing the top of a board". Keep "the rule answers one question: does the leader's score exceed the score of the process that produced the gold", and explicitly state it does not estimate ranking error rate or certify distinguishability of two systems.

- **Section 4 (Noise floor)**: Insert before threshold δ discussion that "clearing producer baseline is not a necessary condition for every resolvable top ordering", referencing synthetic counterexample as footnote or appendix citation.

- **Conclusion**: Change "no public board measured here receives a readable verdict" to "no public board measured here fires the READABLE arm outside the test suite's positive control", and add next paragraph stating C04 external measurement pending status.

- **Limitations** §5: Add paragraph: "The declared producer-baseline gate can refuse a stable, deterministic ordering; therefore clearance of that gate is not a general necessity for resolvable top orderings, as shown by the synthetic counterexample bound to this release."

## Evidence now available (to be added to project.json claims/evidence)

- **C09**: Synthetic construct-validity counterexample (verified). Two-run byte identical; producer_floor=1.0, A=0.9/B=0.5, stable deletions=700/700, paired_discordance=[280,0]; positive control correctly readable at floor=0.8; negative control correctly reversed.

- **C10**: Source lineage recovery (verified): exact manifest blob restored; manuscript differs by +8/-5 lines; publication identity remains unproven.

- **C03 status**: remains blocked until sections above are revised and re-run gates; independent review major issue addressed by narrowing, but review state only updates after code/text changes pass native/compile/archive checks.

## Three alternative positions (choose one and write accordingly)

### 1. Narrowed construct-validity audit (recommended)
Keep the tool and measurements; change narrative to "we identify when consensus-gold constructions fail to yield a verdict, and how design choices determine that outcome." Replace "necessary condition for readability" with "a sufficient condition for refusal under the specific construction."

**Required edits**: Abstract/Intro/Conclusion edits; Limitations expansion; new Figure S1 showing counterexample geometry and single-item deletion stability trace; updated tables for m25/human/gold-degenerate cases (already available).

**Gate status**: after edits + gate recomputation → C03 closed pending independent reviewer sign-off.

### 2. Disjoint-field deployment first
Publish separate arXiv note measuring external leaderboard with model judges disjoint from contestants, where per-judge votes downloadable and gold pool ≠ ranked field. Use this paper only for methods and negative results; do not claim positive wild readings until such data exist.

**Required**: protocol pre-registration, dataset selection rule (≥3 judges, per-judge vote files per judge, explicit license), sample-size calculation, submission-before-review checklist.

**Gate status**: C04 becomes primary target; C03 remains open until narrow positioning adopted elsewhere.

### 3. Merge both
Revise to #1 now, add C04 preregistration draft as next experiment (see below) with timeline and failure modes. Keeps project moving while committing to external measurement.

## Decision rule before writing begins

- Choose one of the three positions above; commit to chosen path in `.qone-revision-proposal/position.txt`.
- Once selected, run gates against current source: no modifications yet; store outputs as `reports/gates/pre-revision-*.json`.
- Re-run gates post-edit; require all gates passed and no regressions in numeric ledger bindings or compile pages before updating CLAIM_LEDGER.md states.

## Next measurement (C04) preregistration skeleton (optional but recommended in parallel)

- **Task**: measure external leaderboard whose gold produced by ≥3 model judges, per-judge votes downloadable, contestants disjoint from judges.
- **Selection rule**: candidate dataset must (a) provide per-judge vote files (JSONL/CSV) with item-level predictions and confidence/logits, (b) have ≥3 distinct judges across ≥1K items, (c) have ranked system list excluding those judges, (d) carry explicit license allowing redistribution or at least local computation of floor.
- **Sample size**: initial feasibility on TruthfulQA-like panels with 5,000–10,000 items; plan for ≥30k items if per-judge variance suggests need.
- **Gates**: same three rulers; strict domain membership check; refusal semantics for m<3 and shared-pool cases; calibrated variant optional.
- **Failure modes**: either no candidate exists in open repositories (limitation statement), or measured case returns UNREADABLE (reinforces limitation of current design), or READABLE appears (positive wild reading).

## Files to create/change

- Draft text edits: `drafts/section-narrowing.md`, `drafts/abstract-edit.md`, `drafts/conclusion-edit.md`
- New figure: `source/figures/fig_counterexample_geometry.svg`
- Pre-registration JSON for C04: `research/pilot-disjoint-field-deployment/preregistration.json` (create after position selection)
- Update `project.json`: add C09/C10 evidence entries and measurements; update notes; regenerate table of claims; re-run claim-ledger verification.
