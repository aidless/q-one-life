# Pipeline state

Status marker: `agent-proposed, not human publication approval`

| Stage | State | Evidence |
|---|---|---|
| Canonical source identity | passed | seven variants re-hashed; canonical `4c530815...` |
| Deprecation marker | passed | explicit banner in the first eight lines |
| Archive marker | passed | retained `MERGED_INTO_tmlr_p12_20260921.md` |
| Merge destination provenance | blocked | `tmlr_p12` contains zero study-specific terms |
| Dataset-scope reconciliation | blocked | synthetic canonical vs three real datasets in four copies |
| E1 recomputation | passed | 240 rows / six dataset-classifier pairs |
| E6 recomputation | passed | 400 rows / K=4 group means |
| Four-class abstract support | blocked | RF `0.2520 -> 0.2662` contradicts "both improve" |
| Resampling headline fields | blocked | named result archive lacks the printed fields |
| Carrier receipts | blocked | 159 PASS / 0 FAIL / 42 absent verdict |
| Review | blocked | retained `5/10`, merge recommendation, two Major findings |
| Independent package | not started | deprecated source and unresolved merge provenance |
| Upload | locked | no package; no authorization |

## Next valid action

Do not build a package from this side shell. If the author later wants to reuse
the content, reconcile the dataset scope, recover the named resampling result
fields and carrier verdicts, and place the material inside the canonical
`tmlr_p12` evidence tree. The merged manuscript must then be re-reviewed
against its new hash. Until then this family remains archived.
