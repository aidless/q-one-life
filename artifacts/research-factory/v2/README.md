# Research Factory v2 artifacts

- `triage.json`: 131-family production queue with transparent factors.
- `triage.md` / `triage.csv`: human-readable queue and editable triage table.
- `pilot-status.json`: eight pilot overlays, claim counts, package states and plan actions.
- `package-audits/`: mechanical LaTeX source-tree audits; never upload authorization.
- `package-audits/index.json`: audit manifest with file hashes.
- `review-packets/`: 131 per-family review packets plus `top20.md`.
- `verification.json`: test, schema, validation, ledger and artifact-hash receipt.

Regenerate the verification, pilot status and package index with:

```bash
PYTHONPATH=src python scripts/research_factory_verify.py
```

Regenerate the review packets with:

```bash
PYTHONPATH=src python scripts/research_review_packets.py \
  --portfolio artifacts/research-paper-portfolio/v1/paper-portfolio.json \
  --triage artifacts/research-factory/v2/triage.json \
  --overlays-root research \
  --output-dir artifacts/research-factory/v2/review-packets
```

No artifact in this directory marks a paper as scientifically ready, accepted,
published, or submitted.
