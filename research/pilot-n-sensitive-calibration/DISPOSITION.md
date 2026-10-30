# P15 disposition

Status marker: `agent-proposed, not human publication approval`

Decision: `merge_archive`

Project status: `archived`

The family is retained as a deprecated source and an evidence-boundary audit.
The canonical manuscript itself says `DO NOT SUBMIT INDEPENDENTLY` and the
project-level merge marker says not to upload, repackage or modify the
manuscript. That is sufficient to stop independent package work.

The destination named by the marker is not textually verified: the pinned
`tmlr_p12` source contains none of the calibration/resampling study terms,
including SMOTE, random undersampling, frozen LLM embeddings or the synthetic
style-classification dataset. The correct record is therefore "archive marker
exists; merge provenance unresolved", not "merge complete".

The four arXiv-labelled source copies also use three real text datasets, while
the canonical source uses one synthetic style-classification dataset. The
dataset scope was never reconciled. E6 further falsifies the abstract's
four-class claim: RF worsens with N at K=4 rather than improving modestly.

No independent candidate package was created. This disposition does not
authorize upload, metadata changes, license changes or a claim that the study
has been successfully merged into the named target.
