# Q-One research overlay: f-acceptance

- Upstream source: `evidence/upstream/main.tex`
- Upstream SHA-256:
  `4c59377876dfe6136c24dd016bca1111918e09a5ecbdf1a4109801795394f797`
- Current overlay source: `source/main.tex`
- Current source SHA-256:
  `986c0a3039e91dc31ad182a2fdaaba643454edd61407b8cfb280c64ef244d5ef`
- Status: `review_pending`
- Target: `arxiv`

The only source change in the overlay is moving the bibliography before the
appendix. The upstream source is retained byte-for-byte and the original
workspace was not modified.

Current evidence:

- `reports/claim-ledger-verification.md`: 13 PASS / 0 FAIL / 1 blocked warning
- `reports/native-verification-gate.json`: 79/79 checks, two identical runs
- `reports/flip-disjointness.json`: 231 versus 9 cell sets, intersection 0
- `reports/cleanroom/receipt.json`: deterministic 14-page compile
- `reports/package/package-receipt.json`: deterministic six-file archive,
  SHA-256 `cf23a62a2c2066a934bea529b6aa97d993df0b78d048c42ceb6ce96620de213a`

The candidate archive is internal. Independent review of the current source,
final metadata, license and upload authorization remain open.
