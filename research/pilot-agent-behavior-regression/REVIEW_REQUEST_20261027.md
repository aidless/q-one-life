# Review request: Paper 35

Review the overlay source at SHA-256
`77f690d40f60fdebd941cc1d2f9031354e050640d21fbef4e3a60444bb76b553`.

The review is evidence-focused and does not authorize upload. The upstream
review remains open with 6 Major and 21 Minor issues; the debate retains 5
Major findings.

## Questions for the independent reviewer

1. Does the 12-file multi-agent cloud-extension replay support only a
   descriptive claim, or is there any valid causal or powered claim?
2. What exact evidence is needed to replay the declared 1,200 full-run cells,
   and which aggregate claims must be downgraded until those raw files exist?
3. Are the category-level comparisons vulnerable to pseudo-replication,
   because the 100 scenarios are the independent unit and cells share
   scenarios? Specify the hierarchical bootstrap or mixed-effects analysis
   required.
4. Is the whitespace-token BDS stable under tokenizer, vocabulary top-K,
   smoothing, response length and paired-condition definitions? Identify the
   minimum sensitivity grid.
5. Are the control experiments sufficient to distinguish token-distribution
   variation from prompt or runtime artifacts?
6. Are the reported cross-seed and cross-model quantities reproducible from
   the frozen analysis files, and which fields remain non-recomputable?
7. Are the 13 citations used at the strength of the underlying claims, and
   does the bibliography need additional methodological references?
8. Do the author, category, abstract, license and release metadata need a
   user decision before this can be considered an arXiv candidate?

## Requested decision

Return one of:

- `scientifically-ready` only if every question has an artifact-bound positive
  answer against the current source hash;
- `major-revision` with itemized evidence requirements;
- `blocked` if the missing raw evidence or source identity prevents review.

The expected disposition is `major-revision` until the raw-cell and
sensitivity gates close. A successful compile or archive is not evidence of
scientific readiness.
