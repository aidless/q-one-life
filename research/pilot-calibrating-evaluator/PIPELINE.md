# Pipeline state

Status marker: `agent-proposed, not human publication approval`

| Stage | State | Evidence |
|---|---|---|
| Canonical source identity | passed | `evidence/source_record.json` |
| Variant reconciliation | passed | `evidence/variant-reconciliation.json` |
| arXiv identity lookup | passed | raw XML and HTTP headers under `evidence/` |
| Driver protocol inspection | passed | `evidence/upstream/calibrated_ttrl.py` |
| Printed-scale reconciliation | blocked | 2,400/3,600 printed versus 1,200/1,800 realized |
| Independent controls | blocked | both controls absent from the driver and output archive |
| Per-seed numeric carrier | blocked | expected JSON absent |
| Model identity reconciliation | blocked | executable IDs disagree with manuscript names |
| Citation mechanical parse | passed | 17/17 keys resolve |
| Citation semantic audit | pending | mechanical resolution is not semantic support |
| Independent method/statistics review | pending | upstream review remains Major Revisions |
| Candidate package | not started | not appropriate after merge/archive disposition |
| Upload | prohibited pending user authority | no upload action was performed |

## Next valid actions

1. Do not create a standalone P9 package from unsupported numbers.
2. If the author later wants P9 promoted, first restore the exact N=5 per-seed
   output, both control archives, parser logs, model endpoint records, and ECE
   data.
3. Bind an independent method/statistics review to the new source hash.
4. Keep the existing arXiv identity as a prior version until a replacement is
   explicitly authorized.
