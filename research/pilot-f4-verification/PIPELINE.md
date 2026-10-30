# Pipeline state

Status marker: `agent-proposed, not human publication approval`

| Stage | State | Evidence |
|---|---|---|
| Source identity | passed | canonical and audit copy have the same SHA-256 |
| Variant inventory | passed | 4 retained source versions, 4 distinct hashes |
| Structure | passed | 15 labels, 28 references, no unresolved reference |
| Citation parse | passed | 42/42 |
| 270-cell pilot | passed | 270 cells, 10 seeds, mean/SD/CI recompute |
| Pooled seed block | passed | 44/12/56, chi-square 17.16, p 2.09e-5 |
| 18,000-trial carrier | blocked | 270 archived cells / 18,000 declared |
| 192/144/90/40 splits | blocked | 0 explicitly named split bundles |
| GPU-hours | blocked | 4.0 declared / 0 runtime carriers |
| 2,700 holds | blocked | 0 numeric leaves contain 2700 |
| Theory headline values | blocked | 0.686, 0.002 and 1.47 have no carriers |
| F4 table | blocked | 4/8 rows disagree; 2 RD denominators; 2 copied intervals |
| Manifest | blocked | 19 match / 7 mismatch / 5 absent / 1 no hash |
| Carrier gate | blocked | 30 PASS / 0 FAIL / 2 NOT_VERIFIABLE |
| Baselines | blocked | printed 0.95/1.05 vs archived 0.82/0.76 and real40 0.00 |
| Author metadata | blocked | canonical email/affiliation differs from arXiv variant |
| Review | blocked | retained score 1/10; no current-hash review |
| Candidate package | not started | no independent evidence closure |
| Upload | locked | no package; no authorization |

## Next valid action

Restore the per-observation records for all 18,000 trials, the four explicitly
named evidence splits and the 2,700 tightness holds; bind per-family GPU runtime
receipts; rebuild every F4 table row and interval from its own counts; regenerate
the manifest over actual experiment records; reconcile baseline and author
metadata; then obtain a new independent review against the frozen hash.

Until that happens the only publishable artifact is a bounded audit or negative
result, and even that requires user decisions on venue, authorship and license.
