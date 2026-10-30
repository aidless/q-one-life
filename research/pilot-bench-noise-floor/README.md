# Q-One research overlay: Benchmark Noise Floor

- Current source: `source/main.tex`
- Current source SHA-256:
  `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca`
- Native-manifest source SHA-256:
  `0d68bda378fa0fc4fe1d39c8c8d46ba39052230fae7a1e8f2fd44b41e5b7e113`
- Status: `revision`
- Target: `arxiv`

The source-hash mismatch is retained. Updating the manifest to match the
current bytes without the original publication record would hide an identity
gap rather than close it.

Current evidence:

- `reports/native-numeric-gate.json`: 250/250 numbers, reverse coverage
  353/350 bound/3 excused/0 unbound, anchor GREEN/A1=0, two identical runs
- `reports/cleanroom/receipt.json`: deterministic 45-page compile
- `reports/package/package-receipt.json`: deterministic eleven-file archive,
  SHA-256 `74218ff9f262a8a57383875faf229a93cbd6a0cf45a2738e17571b1e11900c75`
- `evidence/source-lineage.json`: the native-manifest blob is exactly recovered
  from git commit `9eb77f1b77baaa9932d8faf18da2fc50a2077f6c`; the current source
  remains a later revision and publication identity remains unproven
- `experiments/producer-baseline-counterexample/results/reproduction.json`:
  two byte-identical runs reject the broad producer-baseline necessity claim in
  a declared synthetic construction, with positive and negative controls
- `experiments/bootstrap-estimand-a2/results/run-1.json`: the margin bootstrap
  splits into two estimands. Re-selecting the leader inside each round as well
  as the floor gives a margin of exactly zero in 2000 of 2000 rounds on all four
  `m=25` tasks; the printed interval belongs to the fixed-winner contrast
  (`[-3.90, 0.00]`, `[0.00, 0.00]`, `[-0.71, 0.00]`, `[-1.73, 0.00]`) and is
  never positive in any round. Two controls with a broken hypothesis move the
  same statistic to `[+3.27, +7.35]` and `[-2.68, 0.00]`. Two accepted runs are
  byte-identical and an unmodified native rerun reproduces
  `evidence/m25_factuality.json` byte for byte
- `revisions/2026-10-28-construct-validity-r1/REVISION_R1.md`: a separate
  wording-revision candidate that corrects the producer-baseline interpretation,
  preserves the reported calibrated and disjoint-field measurements, compiles
  deterministically to 45 pages, and keeps the independent review open
- `revisions/2026-10-29-estimand-split-r2/revision-manifest.json`: candidate R2
  builds on R1, binds the A2 experiment and five verification receipts, and
  corrects the falsified coherence sentence; its source
  `fc24f8ef...930c0f` compiles twice to the same 45-page PDF and the candidate
  hash inventory verifies 29/29 entries
- `revisions/2026-10-29-support-threshold-r3/revision-manifest.json`: candidate
  R3 builds on R2 and integrates A3/A4. Its source `a9eef802...e0bb6` compiles
  twice to the same 46-page PDF, the 11-file package audit passes, reverse
  coverage is 355/352/3/0, the anchor census is GREEN with 0 missing anchors,
  verdict-word checks pass 137/137, and the 36-line checksum inventory verifies.
  `REVIEW_REQUEST_R3.md` freezes the A1-A4 review packet and remaining questions
  but has not been sent. This is candidate-level mechanical evidence only
- `experiments/kfold-common-support-a3/results/reproduction.json`: the reported
  `LOO_on_kfold_domain` margins reproduce, but become exactly zero when every
  generator is restricted to the main-gold, LOO-gold, fold-gold and actor
  support. The LOO bootstrap identity is zero in 2000/2000 rounds on all four
  tasks, 0 label mismatches are found, and a non-zero k-fold control remains.
  The preference joint support is only 54 items, so it is descriptive only
- `experiments/threshold-interface-a4/results/reproduction.json`: the pinned
  native CLI has no `--delta` parameter and hard-codes 2.0 points; a derived
  equality fixture is returned as `READABLE` while the R2 candidate says to
  treat equality as `MARGINAL`; and a point margin of `+13.6364` with interval
  `[-100.0000, +21.1240]` is still returned as `READABLE`. Domain, floor and
  no-reading controls remain fail-closed. Two accepted runs are byte-identical
- `reports/claim-ledger-verification.md`: 13 PASS / 0 FAIL / 2 blocked warnings

The candidate archive is internal. Source identity and the independent
producer-baseline review remain blockers. The synthetic counterexample supplies
evidence for narrowing the paper's construct claim; it does not replace a
revision, validation of the native implementation, or an external-gold-pool
study. Revisions R1, R2 and R3 are candidates only and do not overwrite
`source/main.tex`; C02 and C03 remain blockers. A3's support question and A4's
threshold/CLI/equality/CI sub-questions now have reproducible answers and are
integrated in R3, but A4's MDE terminology and generator-independence issues
remain open. R3's compilation and gate passage do not establish scientific
readiness or authorize an arXiv upload.
