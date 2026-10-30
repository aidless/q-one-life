# Q-One research overlay: Paper 35

- Canonical upstream: `evidence/upstream/paper/main.tex`
- Canonical SHA-256:
  `d1eac66806754899440a12bb30446c3944ed230191a077b1bbd331a2ae7a02f0`
- Current overlay source: `source/main.tex`
- Current source SHA-256:
  `77f690d40f60fdebd941cc1d2f9031354e050640d21fbef4e3a60444bb76b553`
- Status: `revision`
- Target: `arxiv`

The canonical upstream is retained byte-for-byte. The overlay removes
template contamination, narrows unsupported claims, records the missing raw
evidence, and replaces the unsupported formal consistency theorem with a
token-frequency proxy. No claim was promoted.

## Current evidence

- `evidence/carrier-audit.json`: 8 frozen carrier receipts pass, 0 fail.
- `evidence/native-audit.json`: 100 scenarios, six category counts, 12
  available multi-agent raw files, 13 resolved citation keys and a recomputed
  cross-model CSV mean.
- `reports/claim-ledger-verification.md`: 11 PASS, 0 FAIL, 4 WARN; only C01
  and C07 are verified.
- `reports/cleanroom/receipt.json`: deterministic 12-page compile.
- `reports/package/package-receipt.json`: deterministic nine-file archive,
  SHA-256 `76d6a55900454c65c76cd9456f2da52fdb69c3d2e1290b882d5d4f9254eb8a81`.

## Open hard blockers

- The full-run manifest declares 1,200 cells, but all 12 raw full-run JSONL
  files are missing. No raw-cell recount was fabricated.
- `evidence/upstream/paper/evidence_manifest.json` has 62 missing entries.
- The upstream review records 6 Major and 21 Minor findings; the debate retains
  5 Major findings.
- BDS sensitivity to tokenization, top-K, smoothing and response length has not
  been independently audited.
- The multi-agent chain analysis is descriptive; causal amplification and
  hierarchical power remain unestablished.
- Final author, category, abstract, license and upload authorization remain
  user decisions.

The candidate archive is internal and is not upload-authorized.
