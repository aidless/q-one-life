# Q-One research overlay: Paper 2 conditional coupling bound

- Canonical upstream: `evidence/upstream/paper/main.tex`
- Canonical SHA-256:
  `379e1632302e979ded0c0462eeba32a07fa82653796ca72d4f9f55e46f8d5cec`
- Current overlay source: `source/main.tex`
- Current source SHA-256:
  `7eb12d1302cf935ab8e19ea425c43da2e72daa89636fd3a5a1e0759bffab8b5d`
- Status: `review_pending`
- Target: `arxiv`

The canonical `paper/main.tex` is retained byte-for-byte. The overlay only
removes stale template text, narrows unsupported release claims, removes a
duplicate section, and replaces off-topic ethics text. No scientific claim was
upgraded.

Current evidence:

- `evidence/carrier-audit.json`: 176 carrier receipts pass, 0 fail.
- `reports/claim-ledger-verification.md`: 14 PASS, 0 FAIL, 2 blocked warnings.
- `reports/cleanroom/receipt.json`: deterministic 14-page compile.
- `reports/package/package-receipt.json`: deterministic three-file archive,
  SHA-256 `561f551d8aa85c4a4fc923110d4a5443d440fcedb545e3164847461924e2d4c5`.

Open hard blockers:

- No independent proof audit.
- No held-out 30-40 condition validation.
- The native `p=0.12` GPT-4o drift statement conflicts with the frozen
  `p_bootstrap=1.0` artifact.
- The native T7 scope count and the frozen T7 output do not agree.
- The meta-review remains open with Major Revisions.
- Final author, category, abstract, license and upload authorization remain
  user decisions.

The candidate archive is internal and is not upload-authorized.
