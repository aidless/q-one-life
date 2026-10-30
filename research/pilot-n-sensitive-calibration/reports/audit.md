# P15 audit report

Status marker: `agent-proposed, not human publication approval`

## Source identity

Seven retained files were hashed. All seven hashes are distinct. The canonical
file is `paper/main.tex` at
`4c530815218543297824cafefa9026e402c0d1fec5528c40d37aaee24b75a475`.

The canonical text begins with `DEPRECATED — DO NOT SUBMIT INDEPENDENTLY` and
states that it was merged into `tmlr_p12` with a unified synthetic + single BGE
scope. The retained archive marker repeats that the side shell must not be
submitted, repackaged or edited.

## Merge destination

The pinned `tmlr-p12/paper/main.tex` has SHA-256
`b406b923bde2bb8b6323d8079ed5edf33f9826056439bd081dcc11d731cb339f`. It has
zero occurrences of the study title, SMOTE, random undersampling, the
resampling calibration audit, frozen LLM embeddings or synthetic
style-classification. This is an unresolved provenance conflict. It does not
prove that the merge failed, but it prevents claiming that it succeeded.

## Dataset scope

The canonical source contains 16 synthetic style-classification mentions and
no "three real text datasets" phrase. The four arXiv-labelled copies contain
zero synthetic style-classification mentions and four "three real text
datasets" phrases. E1 contains 20ng, ag_news and dbpedia rows, so the data
archive aligns with the arXiv copies rather than with the canonical prose.

## Recomputable archive values

E1 has 240 rows and six dataset/classifier pairs at N=500 and N=5000:

| Dataset | Classifier | N=500 | N=5000 | Delta |
|---|---|---:|---:|---:|
| 20ng | RF | 0.3201 | 0.4021 | +0.0820 |
| 20ng | MLP | 0.1987 | 0.0509 | -0.1477 |
| ag_news | RF | 0.3557 | 0.3072 | -0.0485 |
| ag_news | MLP | 0.3608 | 0.0316 | -0.3292 |
| dbpedia | RF | 0.5662 | 0.5828 | +0.0166 |
| dbpedia | MLP | 0.3906 | 0.0288 | -0.3618 |

E6 has 400 rows. At K=4, RF moves from `0.2520` to `0.2662` and MLP from
`0.2032` to `0.0702`. The abstract says both improve modestly at four classes;
the RF direction contradicts that sentence.

## Evidence gaps

`paper/evidence/CARRIER_RECEIPTS.json` has 201 rows: 159 `PASS`, 0 explicit
`FAIL`, and 42 rows with no verdict. The absent-verdict rows are 26 in E1,
10 in E6 and 6 in E8. `results/final_m2_m3_m5.json` also lacks named fields for
the printed SMOTE p-value, Yeast 0.395 ECE, and post-hoc -0.003 AUROC cost.

The retained review card is `5/10` and recommends merging into `tmlr_p12`,
with two Major findings. No current-hash independent review exists.

## Decision

`merge_archive` / `archived`; no candidate package; no upload. The archive
marker is a primary-author instruction, while successful merge provenance
remains blocked.
