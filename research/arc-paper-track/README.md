# ARC Paper Track research overlay

This directory is a Q-One overlay over the existing ARC evidence. It does not
replace or silently update the manuscript or Kaggle writeup.

## Current state

- Remote Kaggle content state: `PUBLISHED` with submitted banner verified.
- Local manuscript: `ARC_REVISED.md`.
- Claim ledger: `CLAIM_LEDGER.md`.
- Ledger verification: `reports/claim-ledger-verification.md`.
- Target in this overlay: arXiv preprint.
- Current status: `revision`.

## Blocking findings

1. The local Markdown SHA-256 is `a07872cc...348c95`, while the current remote
   publication receipt records `a1ff847e...f9fd660`. The local copy must not be
   called the exact published source until it is resynchronized or the remote
   bytes are recovered.
2. The official scoring-methodology source needed by claim C09 is not captured
   locally. C09 remains `inconclusive`.
3. No arXiv source tree, bibliography, cover metadata, or compiled PDF exists
   for this preprint target yet.

## Verification

```bash
python3 /home/liuzewen/.agents/skills/paper-writing-agent/scripts/verify_claim_ledger.py research/arc-paper-track --out research/arc-paper-track/reports/claim-ledger-verification.md
```

The ledger verifier must report 0 FAIL and no uncovered numeric literals.
