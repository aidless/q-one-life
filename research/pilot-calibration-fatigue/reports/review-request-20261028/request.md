# P17 independent review request — internal evidence-repair draft

Status: request prepared locally, not sent.

## Artifact under review

- Source tree: `source/`
- `source/main.tex` SHA-256: `9010a8883bff1b547e31aa10cd29d209fff2a0c261a7ba8423cd0bd7e420e338`
- Can-frozen public baseline remains `evidence/upstream/main.tex` with SHA-256
  `b1de3c420d53f5333d4a522d3e3856c612520667bb209273b86f7ded2af99cd4`.
- Two isolated compilations produced the same 26-page PDF
  `de132dc53ab7d86d7a81de86e57ef28aaf02c097fdcebebda05ffa66c3692f7e`.
- This is not an arXiv submission, not an identified author decision and not a
  scientific-readiness claim.

## Review questions

1. Does any archived local carrier identify GPT-4o for the eight-condition
   Finding-1 design? If not, are the 90.8%, +0.207 and d=4.85 values scoped
   correctly as historical and untraceable?
2. Are Finding-2's gamma≈1.06, 42% and 35–37% statements supported by any raw
   API traces, including model version, N, seeds and bootstrap inputs?
3. Is the revised distinction between the 45-cell mean/range and per-method
   means mathematically correct and sufficiently explicit?
4. Does the T50 ECE reanalysis implement the archived driver definition exactly?
   Does the manuscript avoid treating per-seed recovery as per-round evidence or
   nonsignificance as equivalence?
5. Are theorem assumptions, estimand definitions and dependence structures
   sufficiently explicit for the language used?
6. Are the five retained R16 Major issues closed, narrowed or still open?
7. Is any statement still stronger than its bound evidence?

## Evidence to read

- `CLAIM_LEDGER.md` and `reports/claim-ledger-verification.md`
- `evidence/audit.json`, `evidence/ece-recovery.json`
- `evidence/local-carrier-search.json`, `evidence/candidate-identity-review.json`
- `evidence/citation-identity.json`, `evidence/revision-source.json`
- `reports/cleanroom-internal-20261028/receipt.json`
- `evidence/upstream/REVIEW_R16_summary.md`, `REVIEW_ROUND_6.md`

## Required response

Return findings by severity with file/field references, state whether the
blocked disposition should remain, and distinguish review of engineering
reproducibility from scientific support. Do not infer acceptance or publication.
