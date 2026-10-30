# Authoring brief

Title: **Your Tool-Selection Benchmark May Be Scoring Wrong Calls as Correct**
Target: `arxiv`
Manuscript: `/home/liuzewen/kaggle-control-20261013/paper-evidence/GEMMA_REVISED.md`
Source SHA-256: `aa25d33d83b55c4bff5716f2777f420b182122faf93b26a78694b5ce9c5ea798`

The agent may:

- summarize and reorganize only registered claims;
- draft sections from evidence-bound claims;
- identify missing evidence, citations and experiments;
- propose figures from supplied data and reproducible scripts.

The agent must not:

- invent numbers, experiments, references, authors, licenses or receipts;
- upgrade an `inconclusive` claim to `verified`;
- move a `blocked` claim into the manuscript;
- upload or publish without a separate user action.

Write only after `CLAIM_LEDGER.md` contains the claims relevant to the requested
section. Preserve negative and failed results.
