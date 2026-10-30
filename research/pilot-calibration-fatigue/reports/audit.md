# P17 audit report

Status marker: `agent-proposed, not human publication approval`

## Decision

`blocked` / `blocked`; no candidate package; no upload. The full merged
manuscript is not a duplicate to merge away, but its headline evidence does not
close. The reproducible T30/T50 experiments report null effects and cannot
replace missing Finding-1 and Finding-2 raw traces.

## Source identity and variants

The retained canonical, `main.tex`, has SHA-256
`b1de3c420d53f5333d4a522d3e3856c612520667bb209273b86f7ded2af99cd4`
and is byte-identical to the origin. Its author block and top comment are
anonymous. Fourteen retained source files collapse to eleven hashes. The
arXiv-clean copy and `main.tex.bak_preprint` are the same 540-line, 44,893-byte
three-finding version; the canonical is a 715-line four-finding version with
T50 material. Treating the shorter copy as a completed merge is unsupported.

## Manifest reconciliation

The evidence-directory manifest is complete: 919 of 919 entries match their
size and SHA-256. This does not make every manifest authoritative. The outer
manifest has 4,547 matches, 14 mismatches and 3 absent entries. The arXiv-clean
manifest has 4 matches, 5 mismatches and 17 absent entries; the generated
manifest has 6 matches and 1 mismatch. Packaging must be rebuilt from the
canonical evidence before any future upload.

## Calibration grid

The 72-row deterministic grid contains 45 positive-alpha method/condition
contrasts. Using the cell definition
`100*(CV_N5(method)/CV_N5(none)-1)`, the unweighted mean Delta CV is
`-3.4819%`. The per-method means span `-7.0%` to `-0.6%`, but the actual cell
range is `-28.4083%` to `+33.8601%`. Thus the manuscript's `-7.0% to -0.6%`
range needs an explicit aggregation definition or correction; it is not the
condition-level range.

## Finding 1

The GPT-4o per-repetition factorial archive is absent. Eleven `90.8` carrier
receipts bind to `decomposition.pure_T.paper_pct` in a Qwen 32B cross-model
comparison; that field is a historical manuscript reference, not a measured
Qwen temporal share or a GPT-4o raw trace. Recomputing the Qwen condition means
gives a temporal share of about `-5.15%`, not `90.8%`. The Qwen summary itself
says `NO temporal fatigue (model-specific or null)`. Therefore the 90.8%
headline is blocked, with a model-scope warning stronger than the earlier
"unarchived only" description.

## Finding 2

The `gamma about 1.06`, `42%`, and `35-37%` claims remain absent from the
delivered evidence. Their upstream ledger entries explicitly say traces are
not archived. The local Qwen2 probe is a bounded direction-level pilot, not a
GPT-4o replication. Its reporting mixes individual-row coupling with a
different question-mean calculation at low temperature; that audit caveat must
be retained even though the broad CV direction reproduces.

## T30 and T50

The frozen per-seed JSONs are complete: A/B/C/D have 30 seeds each for both
T30 and T50, all rounds and 5-agent correctness arrays are present, and factor
assignments agree with the directory names. T30 reproduces all four condition
summaries, the 120 CSV rows, and the factorial estimates within `1e-9`.
T50 reproduces the stored overall, early/late and convergence statistics within
`1e-9`. The 30-seed predecessor archive is excluded because A/C/D carry the
same gamma arrays.

At T50, late Communication gamma is `d=-0.1693`, `p=0.3556`, below the
preregistered strengthening threshold of `d>0.30`. This is a null result, not
evidence of equivalence. No per-round ECE field exists in any T50 record, so
the stored NaN ECE means cannot be interpreted as a null effect.

## Citations, correction and review

An earlier scanner reported two missing BibTeX keys. That report was wrong:
it read only `references.bib` and ignored the canonical declaration
`\bibliography{references,refs_added}`. Rechecking both declared files resolves
all 29 cited keys. Primary arXiv/ACL metadata independently matches the two
formerly ambiguous references (`bertalanic2026cost` and `dodge2019reproducibility`).
This closes key and identity resolution for those entries only; sentence-level
claim support for all 29 sources is not established.

The retained R16 review still records missing Finding-1 raw traces, a
non-equivalent DeepSeek replica, unclosed theorem assumptions/dependence, N=5
limitations, and no prospective monitor validation. No review is bound to a
candidate-package hash because no package was created.

## Local carrier search and ECE recovery

A bounded local search covered 10,477 readable JSON/JSONL/CSV files or archive
members under the recorded calibration-family roots. It found 34 eight-condition
candidates reducing to three unique contents, all Qwen runs or summaries; none
identifies GPT-4o. This cannot prove a file is absent from every disk or account,
so the historical 90.8% and Finding-2 values remain blocked.

The T50 archive stores no per-round ECE, but it does retain confidence and
correctness arrays. Reapplying the archived driver's 10-bin, rank-sorted
definition reproduces all 120 stored per-seed ECE values exactly from 30,000
observations. The T50 ECE Communication contrast is `d=-0.0031`, `p=0.9864`;
Calibration is `d=0.0699`, `p=0.7024`. These are new retrospective estimates,
not preregistered phase tests, and nonsignificance is not equivalence.

## Internal revision

The separate `source/` tree fixes only evidence-supported presentation issues:
it labels the document as an internal draft, states the missing historical raw
trace, distinguishes per-method-mean and cell-level CV ranges, and replaces
"no effect" with "nonsignificant, not equivalence." It leaves authors, license
and publication state unchanged. Two isolated compilations yielded identical
26-page PDFs (`de132dc5...`) with no unresolved citations. Compilation is not
scientific readiness.

## Reproduction

```bash
python research/pilot-calibration-fatigue/tools/audit_p17.py --self-test
python research/pilot-calibration-fatigue/tools/audit_p17.py
python research/pilot-calibration-fatigue/tools/search_carriers.py
python /home/liuzewen/.agents/skills/paper-writing-agent/scripts/verify_claim_ledger.py \
  research/pilot-calibration-fatigue \
  --out research/pilot-calibration-fatigue/reports/claim-ledger-verification.md
```

The audit reads frozen copies under the overlay; it does not execute upstream
analysis scripts or write to the research source. The self-test proves that
tampering, absent files, path escape, missing citations across multiple BibTeX
files, range aggregation, invalid ECE inputs and numeric drift are detected.
