# Q-One research overlay: N-sensitive calibration archive

Status marker: `agent-proposed, not human publication approval`

- Family: `qf-n-sensitive-calibration-of-tree-ensemble-623d15100e`
- Project: `qp-tmlr-resampling-calibration-632b05b06c33`
- Canonical SHA-256:
  `4c530815218543297824cafefa9026e402c0d1fec5528c40d37aaee24b75a475`
- Disposition: `merge_archive`
- Project status: `archived`
- Package: none
- Uploaded: no

## What is auditable

- Seven retained source versions have seven distinct hashes.
- The canonical manuscript begins with `DEPRECATED — DO NOT SUBMIT
  INDEPENDENTLY` and says the work was merged into `tmlr_p12`.
- The archive marker independently says not to submit or repackage the study.
- E1 has 240 per-seed rows and reproduces six RF/MLP N=500 to N=5000
  adaptive-ECE pairs.
- E6 has 400 per-seed rows; its K=4 result is reproduced exactly.
- The source record, variant reconciliation, claim values and claim ledger all
  retain hashes so the disposition can be rechecked.

## Why this is archived rather than packaged

- The canonical source forbids independent submission and packaging.
- The named `tmlr_p12` target contains none of this study's identifying terms;
  the archive marker is evidence of intent, not proof that the merge completed.
- The canonical source describes a synthetic style-classification study, while
  four arXiv-labelled source copies describe three real text datasets. This is
  an unresolved scope conflict, not a cosmetic variant difference.
- E6 contradicts the abstract's four-class sentence: RF worsens from `0.2520`
  to `0.2662` while MLP improves from `0.2032` to `0.0702`.
- The resampling headline values (`p=0.13`, Yeast `0.395`, post-hoc `-0.003`)
  lack named fields in the retained `final_m2_m3_m5.json`.
- Of 201 carrier receipts, 159 have `PASS`; 42 have no verdict at all, with 26
  in E1, 10 in E6 and 6 in E8.
- The retained review is `5/10`, recommends merging and still records two
  Major findings.

No independent candidate package was fabricated from a deprecated source.
