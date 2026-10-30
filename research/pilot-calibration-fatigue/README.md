# P17 calibration-fatigue audit

Family: `qf-calibration-fatigue-self-evaluation-frag-3c06d49517`

Project: `qp-calibration-merged-full-from-data3-ec845c511c6b`

This overlay freezes the canonical merged source, source variants, result
archives and review records for the calibration-fatigue manuscript. It exists
to test whether the four headline findings have reproducible raw carriers.

Result: `blocked`. The T30/T50 archives reproduce and remain null; the main
Finding-1 and Finding-2 headlines lack usable raw carriers; the older 30-seed
archive is corrupt; outer/arXiv manifests remain stale. All 29 canonical
citation keys resolve once both declared BibTeX files are scanned. T50
per-seed ECE was recovered from archived confidence/correctness pairs; no
per-round ECE exists. A separate internal `source/` revision compiles
 deterministically but is not a publication candidate.

No candidate package was created. No source, author, license or account data
was changed, and nothing was submitted or uploaded.

Run `python tools/audit_p17.py --self-test` and then `python tools/audit_p17.py`.
The detailed boundary is in `reports/audit.md`; disposition is in
`DISPOSITION.md`.
