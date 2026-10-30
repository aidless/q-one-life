# P16 disposition

Status marker: `agent-proposed, not human publication approval`

Decision: `merge_archive`

Project status: `archived`

The family is retained as a deprecated source and an evidence-boundary audit.
The canonical manuscript says `DO NOT SUBMIT INDEPENDENTLY`, and the retained
archive marker says not to submit, upload, repackage or edit the side shell.
That instruction is sufficient to stop independent package work.

The marker names `tmlr_p12` as the canonical destination. The pinned p12 source
contains 45 occurrences of `N-sensitivity`, but zero study-specific data, model
or result terms. The correct record is therefore "merge intent present;
merge provenance unresolved", not "merge complete" or "merge failed".

The source is also internally unstable: its dataset scope changes between
synthetic style-classification and Newsgroups snapshots; the title promises a
resampling study but the text contains no SMOTE or undersampling experiment;
snapshot AUROC and Brier values contradict the main table; and the N-sensitivity
table and correlations do not reproduce exactly. These are scientific-scope
and evidence-binding failures, not layout defects.

The retained review is `2/8`, D veto / reject, while the R16 record asks for a
Major Revision. No current-hash independent review closes those findings.

No independent candidate package was created. This disposition does not
authorize upload, metadata changes, license changes or a claim that the study
has been successfully merged into the named target.
