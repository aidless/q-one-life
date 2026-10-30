# Q-One research overlay: hidden-cost / resampling archive

Status marker: `agent-proposed, not human publication approval`

- Family: `qf-the-hidden-cost-of-resampling-how-imbala-36f86aadfa`
- Project: `qp-tmlr-tmlr-p6-60e62c7566d9`
- Canonical SHA-256:
  `b1ea39681d0b89002fd520f816dea590d5daccf1cea1c5c106a703c544fcefba`
- Disposition: `merge_archive`
- Project status: `archived`
- Package: none
- Uploaded: no

## What is auditable

- Seven retained source files have seven distinct SHA-256 hashes. The
  `arxiv/main.tex` copy is byte-identical to the canonical source and is not
  counted as another version.
- The canonical manuscript starts with `DEPRECATED — DO NOT SUBMIT
  INDEPENDENTLY` and says it was merged into the N-sensitivity main paper
  `tmlr_p12`.
- The retained archive marker independently says not to submit, upload,
  repackage or edit the side shell.
- The 195431 snapshot can be recomputed from ten per-seed rows. Its AUROC and
  Brier values do not match the values printed in the manuscript.
- The five-point N-sensitivity archive can be recomputed, but one rounded cell
  and both reported correlations disagree with the archive.
- The claim ledger, source record, variant reconciliation, carrier audit and
  generated values retain hashes and deterministic inputs.

## Why this is archived rather than packaged

- The canonical source and the archive marker both forbid independent
  submission. That instruction is sufficient to stop package work.
- The named `tmlr_p12` target contains 45 occurrences of `N-sensitivity`, but
  zero matches for the study data, models or identifying result terms. This
  establishes shared vocabulary, not that the merge completed.
- The canonical text describes a 996-sample, six-class synthetic
  style-classification study with BGE-small-zh-v1.5, while the main 195431
  snapshot is 1,000-sample, eight-class Newsgroups data with MiniLM. The
  N-sensitivity archive is another five-seed Newsgroups/BGE-zh run.
- The title says `resampling`, but the manuscript contains one `resampl` match,
  zero SMOTE mentions and zero undersampling mentions. No resampling experiment
  is present in the retained source.
- Snapshot ECE values are MLP `0.1410`, RF-Embed `0.0957`, RF-Hybrid `0.0899`
  and RF-Tabular `0.0606`. Snapshot AUROCs are `0.8667`, `0.8778`, `0.8754`
  and `0.6601`, not the printed `0.992/0.989/0.990/0.941`. Snapshot Brier
  scores are `0.5752/0.4579/0.4617/0.6968`, not
  `0.089/0.071/0.065/0.118`.
- Isotonic calibration reduces RF-Hybrid ECE by 24.86%, not 99%, and changes
  AUROC by `-0.0378`, not `0.037`.
- Twelve of 15 pairwise tests are nominally significant, but only 10 survive
  Bonferroni correction. The manuscript's corrected `12/15` is unsupported.
- All 57 carrier receipts are mechanically `PASS`, but 42 bind the printed
  number to a different quantity, model, run or prose role. Mechanical
  reachability is not semantic evidence binding.
- The retained review is `2/8`, D veto / reject, and the R16 summary requires
  Major Revision.

No independent candidate package was fabricated from a deprecated source.
