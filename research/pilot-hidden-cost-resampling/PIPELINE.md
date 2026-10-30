# Pipeline state

Status marker: `agent-proposed, not human publication approval`

| Stage | State | Evidence |
|---|---|---|
| Canonical source identity | passed | seven distinct hashes; canonical `b1ea3968...` |
| Deprecation marker | passed | explicit banner in the first five lines |
| Archive marker | passed | retained `MERGED_INTO_tmlr_p12_20260921.md` |
| Merge destination provenance | blocked | p12 shares N-sensitivity vocabulary but zero study-specific terms |
| Dataset-scope reconciliation | blocked | six-class synthetic canonical vs eight-class Newsgroups snapshot |
| Title/content scope | blocked | one `resampl` match; zero SMOTE and zero undersampling experiments |
| Main table recomputation | blocked | snapshot AUROC and Brier values contradict printed values |
| Isotonic recomputation | blocked | ECE falls 24.86%, not 99%; AUROC changes by `-0.0378` |
| Pairwise significance | blocked | 12 nominal, only 10 Bonferroni-significant; text says 12 corrected |
| N-sensitivity table | blocked | one rounded cell and two correlations disagree |
| Carrier semantic binding | blocked | 57 mechanical PASS; 42 wrong quantity/model/run/role |
| Anonymity metadata | blocked | record says anonymous; source names Zewen Liu and uses preprint |
| Retained review | blocked | `2/8`, D veto / reject; R16 requires Major Revision |
| Independent package | not started | deprecated source and unresolved merge provenance |
| Upload | locked | no package; no authorization |

## Next valid action

Do not build a package from this side shell. If the author later wants to reuse
the material, move it into the canonical `tmlr_p12` evidence tree, choose one
dataset scope, restore the named resampling result fields, rebuild semantic
carriers and re-review the merged source at its new hash. Until then this family
remains archived.
