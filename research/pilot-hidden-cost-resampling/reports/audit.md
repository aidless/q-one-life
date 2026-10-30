# P16 audit report

Status marker: `agent-proposed, not human publication approval`

## Source identity

Seven retained files were hashed and all seven hashes are distinct. The
canonical file is `paper/main.tex` at
`b1ea39681d0b89002fd520f816dea590d5daccf1cea1c5c106a703c544fcefba`.
The `arxiv/main.tex` copy is byte-identical and is not counted as another
version.

The canonical text begins with `DEPRECATED — DO NOT SUBMIT INDEPENDENTLY` and
says it was merged into `tmlr_p12`. The retained archive marker repeats that
the side shell must not be submitted, uploaded, repackaged or edited.

## Merge destination

The pinned `tmlr-p12/paper/main.tex` has SHA-256
`b406b923bde2bb8b6323d8079ed5edf33f9826056439bd081dcc11d731cb339f`. It
contains 45 occurrences of `N-sensitivity`, but zero occurrences of the study
title, SMOTE, random undersampling, isotonic calibration, frozen embeddings,
BGE-small-zh-v1.5, synthetic style-classification, RF-Hybrid or MLP-Embed.
This is unresolved merge provenance, not evidence that the merge failed.

## Scope and title

The canonical prose describes a 996-sample, six-class synthetic
style-classification study with BGE-small-zh-v1.5 and ten seeds. The main
195431 snapshot is 1,000-sample, eight-class Newsgroups with MiniLM and ten
seeds. The N-sensitivity archive is a separate five-seed Newsgroups/BGE-zh run
over N = 200, 500, 1,000, 2,000 and 5,000.

The title contains `Resampling`, but the manuscript has one `resampl` match,
zero SMOTE mentions and zero undersampling mentions. No resampling experiment
is present in the retained source.

## Snapshot recomputation

The 195431 snapshot was recomputed from all ten per-seed rows:

| Model | ECE | AUROC | Brier | Accuracy |
|---|---:|---:|---:|---:|
| MLP-Embed | 0.140982 | 0.866748 | 0.575179 | 0.661692 |
| RF-Embed | 0.095707 | 0.877766 | 0.457911 | 0.697512 |
| RF-Hybrid | 0.089854 | 0.875383 | 0.461715 | 0.688060 |
| RF-Tabular | 0.060638 | 0.660141 | 0.696810 | 0.410448 |

The manuscript prints AUROC `0.992/0.989/0.990/0.941` and Brier
`0.089/0.071/0.065/0.118`. Neither set matches the retained snapshot.

RF-Hybrid isotonic calibration changes ECE from `0.089854` to `0.067521`, a
24.86% reduction rather than 99%. AUROC changes from `0.875383` to `0.837549`,
or `-0.037834`.

Of 15 pairwise Wilcoxon tests, 12 are nominally significant and only 10 survive
Bonferroni correction. The printed corrected `12/15` is false. The two
nominal-only pairs are MLP-Embed-Isotonic vs RF-Hybrid (`p=0.00390625`,
corrected `0.05859375`) and RF-Embed vs RF-Hybrid (`p=0.037109375`, corrected
`0.556640625`).

## N-sensitivity

| N | RF-Hybrid | RF-Embed | MLP-Embed |
|---:|---:|---:|---:|
| 200 | 0.165175 | 0.150493 | 0.130341 |
| 500 | 0.105718 | 0.115784 | 0.147601 |
| 1000 | 0.102984 | 0.101739 | 0.129365 |
| 2000 | 0.093534 | 0.085987 | 0.130439 |
| 5000 | 0.083227 | 0.083402 | 0.134494 |

RF-Embed N=200 rounds to `0.150`, not the printed `0.151`. RF-Hybrid Pearson
correlation is `-0.666` with linear N and `-0.884` with log10(N), not `-0.973`.
MLP linear correlation is `-0.120`, not `+0.078`.

## Carrier receipts

`CARRIER_RECEIPTS.json` has 57 rows and all are mechanically marked `PASS`.
Semantic inspection finds 42 misbindings:

- 33 bind the printed value to a different quantity;
- 3 bind the wrong model or run label;
- 6 bind the wrong snapshot or seed.

Examples include AUROC values bound to reliability-bin confidence, Brier scores
bound to accuracy standard deviation or per-class ECE, a correlation bound to
accuracy standard deviation, and `BGE v1.5` bound to a training-time field.
Therefore 57 mechanical `PASS` verdicts do not prove 57 valid claims.

## Metadata and review

`manuscript_anonymity.json` records an anonymous author, while canonical
`main.tex` contains the named author Zewen Liu and the preprint option. The text
also contains two Limitations sections, says there was no sample-size sweep
while containing a five-point N-sensitivity table, and says all models achieve
perfect accuracy although snapshot accuracy ranges from 0.4104 to 0.6975.

The retained review card is `2/8`, D veto / reject, and the R16 summary requires
Major Revision. No current-hash independent review closes the findings.

## Decision

`merge_archive` / `archived`; no candidate package; no upload. The archive
marker is a primary-author instruction, while successful merge provenance and
the scientific evidence boundary both remain unresolved.
