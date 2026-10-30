# Disposition

- Decision: `blocked`
- Project status: `blocked`
- Candidate package: none
- Upload: none
- Scientific readiness: not established
- Internal revision: `source/main.tex`, 8 files, deterministic 26-page clean-room PDF; not a candidate package

The manuscript is the only retained complete four-finding version, so it is not
a duplicate to discard. Release is nevertheless blocked: Finding-1 lacks
GPT-4o raw per-repetition traces and its 90.8% receipts partly point to a
historical reference; Finding-2's 1.06, 42% and 35-37% values lack raw API
traces; A/C/D in the predecessor archive are identical; the outer and
arXiv-clean manifests disagree with retained files; two citations are missing;
and no current-hash method/statistics review closes the retained majors.

What would unblock a later decision:

1. Restore GPT-4o Finding-1 raw per-condition/per-repetition traces and the
   exact decomposition inputs; recompute 90.8% and bind every printed instance.
2. Restore Finding-2 raw traces for 1.06, 42% and 35-37%, including model
   versions, N, seeds and bootstrap inputs.
3. Retire the corrupt 30-seed predecessor archive from formal inference.
4. Rebuild a scoped manifest from canonical evidence. Citation keys now resolve
   across both BibTeX files; review support for all cited claims remains open.
5. Close independent method/statistics review against the new source hash.
6. Re-run clean-room packaging only after the above; upload remains a user gate.
