# Independent review request: Benchmark Noise Floor

Review type: method and construct validity, model-assisted or human

## Frozen target

- Project: `research/pilot-bench-noise-floor`
- Manuscript: `source/main.tex`
- Current source SHA-256:
  `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca`
- Native-manifest source SHA-256:
  `0d68bda378fa0fc4fe1d39c8c8d46ba39052230fae7a1e8f2fd44b41e5b7e113`
- Candidate archive:
  `reports/package/noise-floor-arxiv-candidate.tar.gz`
- Candidate archive SHA-256:
  `74218ff9f262a8a57383875faf229a93cbd6a0cf45a2738e17571b1e11900c75`

The source-hash mismatch is intentionally retained and must not be silently
fixed by updating the manifest.

## Required evidence

1. `CLAIM_LEDGER.md` and `reports/claim-ledger-verification.md`
2. `reports/native-numeric-gate.json`
3. `reports/native-ledger-audit.json`
4. `reports/package-audit.json`
5. `reports/cleanroom/receipt.json`
6. `reports/package/package-receipt.json`
7. `evidence/REVIEW_INDEPENDENT_2026-10-24.md`
8. Native ledger and manifest under `evidence/`

## Review questions

1. Is the producer baseline a valid comparator for the claimed notion of
   leaderboard readability, or does the construction measure a different
   quantity?
2. Can the issue be closed by narrowing the paper's claim to a construct-
   validity audit, or does it require a new external gold pool disjoint from
   the ranked systems?
3. Do the three numeric rulers support only their stated domains and refusal
   semantics?
4. Do the 569-entry ledger audit, reverse coverage, and anchor census provide
   adequate numeric traceability despite the manifest mismatch?
5. Are there any remaining Critical or Major statistical, construct-validity,
   reproducibility, or writing defects?

## Output contract

- Write a read-only review report with severity, finding, evidence location,
  and exact requested revision.
- Bind the report to the current source SHA-256 above.
- State explicitly whether the producer-baseline issue is resolved, must be
  narrowed, or requires new evidence.
- End with one disposition: `pass`, `minor-revision`, `major-revision`, or
  `blocked`.

Do not modify the manuscript, manifest, package, project state, or external
services.
