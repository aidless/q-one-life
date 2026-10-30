# submission_variant

`main.tex` here is the **anonymous TMLR submission** form of this paper.

Parent `source/main.tex` uses `\usepackage[preprint]{tmlr}`, which is the **arXiv preprint** form:
it sets both `\@preprinttrue` and `\@acceptedtrue` inside `tmlr.sty`, so the
rendered output is de-anonymised. That is correct for a preprint server and a
G3 violation for a TMLR submission, which must use `\usepackage{tmlr}` with
**no option**.

This directory differs from the parent only in that one macro option. The
parent file is left untouched, because the preprint is a separate deliverable
with its own purpose.

Verified 2026-09-26: the variant compiles, every page carries "Under review as
submission to TMLR", and no page contains "Published in Transactions".
