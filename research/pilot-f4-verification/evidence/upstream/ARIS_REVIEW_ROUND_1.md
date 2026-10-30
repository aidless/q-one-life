REVIEW_TIER=isolated-subagent cross_family_channel=absent verdict=BLOCKED
Reviewer=research-review-REVIEW_ROUND_1-01
Reviewed_utc=2026-09-29T07:16:37Z
Run=runs/tmlr-f4-verification  (all paths below are relative to P=/home/liuzewen/Projects/agi-paper-pipeline)
Round=1  first review this manuscript has received in this chain; no prior verdict for this tier exists in the slot directory.

## Live-tree integrity (open / close)

Measured with `hashlib.sha256` on the live run; the run was not written to at any point.

| file | sha256 @ open | sha256 @ close | bytes |
|---|---|---|---|
| `paper/main.tex` | `f48ea4e93d9d442cbc62da077cd664291c3c4e44a834bcdb4f19aba6f62416e2` | `f48ea4e93d9d442cbc62da077cd664291c3c4e44a834bcdb4f19aba6f62416e2` | 27670 |
| `paper/main.pdf` | `acb2725a2f87471a31a166392e36f6e2047e76e09c5179fc4985ca67dd679b45` | `acb2725a2f87471a31a166392e36f6e2047e76e09c5179fc4985ca67dd679b45` | 515345 |
| `paper/evidence/CARRIER_RECEIPTS.json` | `1d48b640f6bec47625dcf17a78fbbd9cce5a7780b740f22d714716a6daf77537` | `1d48b640f6bec47625dcf17a78fbbd9cce5a7780b740f22d714716a6daf77537` | 10759 |

Whole-tree digest over all 160 files in the run (excluding only my own verdict file): before
`c71127a12be79aacea240501e4cb15af7a1c17685207a7b1ef1b34952f1ebec8`, after
`c71127a12be79aacea240501e4cb15af7a1c17685207a7b1ef1b34952f1ebec8` — unchanged. `source/` was
compared only, never written (`source/main.tex` is 27973 B / `bc3114fc46dd3a4a…`, distinct from
`paper/main.tex` 27670 B / `f48ea4e93d9d442c…`; the ingest copy and the working copy differ by 303 bytes).
All byte-mutating work happened on `cp -a`-equivalent copies made with
`shutil.copytree(..., symlinks=True)` at `/tmp/f4r1_live` and `/tmp/f4r1_mut` (the run tree contains 0 symlinks:
`find runs/tmlr-f4-verification -type l | wc -l` = 0). Compilation was run only in `/tmp/f4r1_live/paper`.

## Seed count I measured (not the abstract's, not the brief's)

**Ten distinct seeds.** Command and result:

    cd runs/tmlr-f4-verification/paper/evidence && python3 -c "
    import json
    rs=[json.loads(l) for l in open('per_seed_b_c.jsonl').read().splitlines() if l.strip()]
    print('records',len(rs),'distinct seeds',len(set(r['seed'] for r in rs)),sorted(set(r['seed'] for r in rs)))"
    records 10 distinct seeds 10 [42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

`wc -l paper/evidence/per_seed_b_c.jsonl` returns **9**, and the brief's "9 lines" is that number. It is a
newline count, not a record count: `python3` on the raw bytes gives `bytes 782, LF 9, CRLF 9, ends with newline
False` — CRLF line endings plus no terminator on the last record, so the tenth record (seed 51) is invisible to
`wc -l`. I therefore **reject the brief's premise that a 9-record file cannot support a 10-seed claim**: the
carrier does hold 10 per-seed records, and the abstract's "10-seed" count is arithmetically right about that
file. The real defect is adjacent and is BL-4/MAJOR-2 below: only 3 of those 10 seeds reach any printed number.

## Build judgement (from the product, not the exit code)

`/tmp/f4r1_live/paper`: `xelatex` → `bibtex` → `xelatex` ×3. Exit codes 0/0/0/0/0.
`grep -c "^!" main.log` = 0 on every pass; `grep "LaTeX Warning" main.log` = 0 hits; `grep -n "undefined"
main.log` = 0 hits; `main.bbl` has 42 `\bibitem`s and `refs.bib` has 42 `^@` entries (`grep -c "^@"
paper/refs.bib` = 42). `pdfinfo` = 12 pages. Cross-reference integrity over `paper/main.tex` +
`paper/sections/*.tex`: **0 referenced-but-undefined**, 3 defined-but-never-referenced
(`tab:f4`, `tab:full12`, `sec:evidenceinventory`) — see MAJOR-6. The build is clean; the manuscript's problem
is not the build.

## Length instrument (measured honestly)

    $ python3 tools/body_pages.py runs/tmlr-f4-verification
    tmlr-f4-verification               body=  8.67  total= 12  ends p9 (frac 0.67) [appendix] A Appendix I: Extended Related Work Comparis
    $ python3 gates/page_standard.py --root runs/tmlr-f4-verification
      floor: body >= 8 pages   ceiling: none
      measured body: 8.67 pages of 12 total (paper/main.pdf <- paper/main.tex)
      boundary: appendix on page 9 at 67% down the page, matched line 'A Appendix I: ...'
      structure (paper/main.tex): 11 sections, 1 figures, 7 tables, 4202 body words, undefined refs: 0
    PASS: page standard

Both ran read-only (`gates/page_standard.py` writes only inside `--self-test`/`--json-out`, lines 207–230 and
334 of that file; I passed neither flag), and the tree digest above is unchanged after them. The floor is met by
0.67 pages. What meets it is the point of MAJOR-3 and MINOR-1: the three generated audit sections
(`sections/evidence_inventory.tex` ~521 words, `sections/baselines_audit.tex` ~290, `sections/manifest_audit.tex`
~794 = ~1605 words, ~32% of the ~5050-word body) occupy pages 6–9 of the measured body, i.e. roughly 3.7 of the
8.67 body pages, and they report **no experiment** — they are bookkeeping about which claims lack evidence. The
research content is thin by comparison: `Theory` is 105 words and `Discussion` 115 words (measured by stripping
LaTeX tokens from main.tex:116 and :168). So the floor is cleared by volume of disclosure prose, not by substance
of results. Note also that the section literally named "Extended Main Text for 12-page Journal Version"
(`paper/main.tex:208`) sits **after** `\appendix` (`paper/main.tex:190`), so it contributes nothing to the 8.67 —
the page-padding device does not even touch the instrument that scores the floor.

## Census mirror check (my measurement, on /tmp)

    $ python3 tools/manuscript_literal_census.py --run /tmp/f4r1_live
    f4r1_live: 106 distinct literals / 165 occurrences — CARRIER 19 / SCREEN_ONLY 33 / ASSERTED_NOT_RUN 0 / NO_CARRIER 113

This reproduces the brief's 07:00Z figures and `paper/EVIDENCE_RECORD.md:27` exactly. The census is **not** inert:
on the mutated copy it moved to `CARRIER 16 / SCREEN_ONLY 36`, so it does respond to raw data (see BL-2).
My adjudication of the 33 SCREEN_ONLY rows is in MINOR-1: I opened every one of their bases and **not a single
one is the same quantity at the same precision** — they are rounding and substring accidents, several of them
matched against the author's own review files (`source/reviews/ten_review_*.json#risk.risk`).

Of the 19 CARRIER occurrences, my split from `paper/evidence/CARRIER_RECEIPTS.json` and the census basis strings:
**7 re-execute a derivation** (`17.16`, `3.37`, `7.58`, `4.50`, `0.064`, `0.0044`, `0.031`) and **12 are a
transcription of one leaf** of the baked derived table (all four `RD` values and all eight CI endpoints,
including the headline `+0.107`/`[+0.058,+0.156]`). So **7 of 165 printed decimal occurrences — 4.2% — are
re-executed from raw data**, and every one of them is a χ² or a p on the four seed rows. That is the honest
denominator, and it is materially worse than the "19" the record prints.

## Findings

### BLOCKING

**BL-1 — The headline pooled McNemar risk difference is exactly 3× its own components; the printed CI excludes the correct value.**
`paper/main.tex:152` prints `Seed-pooled 42/43/44 | 44/12 | 56 | +0.107 | [+0.058,+0.156] | 17.16 | 2.09e-5`.
The pooled `RD` is computed as `(b−c)/N_PAIRED` with `N_PAIRED = 300` over `SEEDS = (42, 43, 44)`
(`.aris/f4_table2_seed_rows.py:39`, `:41`, `:63`, pooled call at `:96`), i.e. discordants summed across three
300-pair tables but divided by one table's n. Recomputed independently (command in the section below): printed
pooled `RD = 0.10667`; mean of the three single-seed RDs printed two rows below = `0.03553`; ratio = **3.002**.
The pooled RD over 3×300 pairs is `32/900 = 0.0356`, whose own 95% Wald interval is `[0.019, 0.052]`. The
printed interval `[+0.058,+0.156]` **excludes** the correct point estimate. The carrier's own `RD` field proves
the intended denominator is per-seed (`b − c = 300·RD` holds for each record; I verified `n_d == b+c` for all 10
records). This is not a stale fossil — the caption at `paper/main.tex:143` presents this round's rewrite as the
fix, and `ROUND_20260928T0614Z.md:60-64` argues the `n=300` choice is "not my assumption". It is right for the
three single-seed rows and wrong for the pooled row, and the pooled row is the row the paper sells.

**BL-2 — 12 of the 32 receipts re-read a baked derived table instead of re-executing the pooling; the headline RD/CI claims have no live carrier.**
`paper/evidence/CARRIER_RECEIPTS.json` has 32 rows; 12 carry `locator` into
`paper/evidence/f4_table2_seed_rows.json` (`rows.pooled.RD`, `rows.pooled.ci_lo`, `rows.pooled.ci_hi`,
`rows.42/43/44.RD/ci_lo/ci_hi`). Nothing regenerates that file on measurement: `grep -rln f4_table2_seed_rows
gates/ tools/ tests/` returns **no files**, so the only writer is the one-off `.aris/f4_table2_seed_rows.py:253`
(`DER.write_text(...)`, mtime 2026-09-28 14:13).
Today the baked values do equal a recomputation from the raw carrier — my independent re-implementation of its
own declared `method` string produced **0 mismatches** across 8 fields × 4 rows — so this is not a "the summary
is wrong now" finding. It is a carrier-shape finding. I mutated one raw record on a `/tmp` copy
(`per_seed_b_c.jsonl` seed 44 `c: 4→5`, `n_d: 18→19`, `RD` recomputed) and re-ran the instrument:

    $ python3 tools/carrier_receipts.py --run /tmp/f4r1_mut      # live copy for contrast: PASS=32 FAIL=0 NOT_VERIFIABLE=0
    f4r1_mut: PASS=25 FAIL=7 NOT_VERIFIABLE=0 (total 32)
      FAIL  12    derived 13 -> 13.0, manuscript says 12
      FAIL  56    derived 57 -> 57.0, manuscript says 56
      FAIL  17.16 derived 15.789473684210526 -> 15.79, manuscript says 17.16
      FAIL  4     derived 5 -> 5.0, manuscript says 4
      FAIL  18    derived 19 -> 19.0, manuscript says 18
      FAIL  4.50  derived 3.3684210526315788 -> 3.37, manuscript says 4.50
      FAIL  0.031 derived 0.063568115234375 -> 0.06, manuscript says 0.031

Every raw-backed row moved; **all 12 locator-backed rows stayed PASS**. Concretely: after the mutation the true
seed-44 RD is `(14−5)/300 = 0.030`, yet the printed `+0.033` and CI `[+0.006,+0.061]`
(`paper/main.tex:155`) are still certified; the true pooled RD becomes `(44−13)/300 = 0.1033`, yet the printed
`+0.107` and `[+0.058,+0.156]` (`paper/main.tex:152`) are still certified. The point estimates and every
interval endpoint the reader is asked to believe are attested by a transcription of a table that no gate
re-executes. Filed at `paper/evidence/CARRIER_RECEIPTS.json` rows 4–6, 12–14, 20–22, 28–30.

**BL-3 — The abstract asserts a statistical result the body withdraws as having no carrier.**
`paper/main.tex:25`: "global comparison uses Friedman over $4\times 6$ ($p{=}0.002$, Nemenyi CD$=1.47$) showing
no significant dominance." `paper/main.tex:119`: "The global comparison an earlier draft attributed to a Friedman
test … **is not reported here: neither statistic appears in any data file in the archive** (Table
`tab:claimcarrier` lists both as `NO_CARRIER`)". I searched every JSON numeric leaf in the run for 0.002/1.47:
no leaf holds either as that quantity (my scan; and `paper/sections/evidence_inventory.tex:30,40` lists both as
`NO_CARRIER`). Both statements are in the **rendered** text layer (`/tmp/render.txt`, extracted with `pdftotext`:
"global comparison uses Friedman over 4×6 (p=0.002, Nemenyi CD= 1.47)" on p.1, the withdrawal on p.4). An
abstract that reports a withdrawn test is a claim–evidence failure independent of whether the statistic is real.

**BL-4 — Four of the "six studies" are not on disk, and the two that are share no verifier pool, model, or task, so pooling McNemar b/c across them is not licensed.**
`paper/main.tex:25` names `tmlr_p6, tmlr_p10, tmlr_p11, tmlr_p12, tmlr_p13, tmlr_p14`. `ls runs/ | grep -Ei
'p(6|9|10|11|12|13|14)'` returns only `p9-pilot`, `tmlr-tmlr-p12`, `tmlr-tmlr-p6`, `tmlr-tmlr-p9`: **no run
directory exists for p10, p11, p13 or p14**. `ls -d runs/tmlr-tmlr-p12/paper` → "没有那个文件或目录" (p12 has no
`paper/` tree at all). What the two extant studies actually did: `runs/tmlr-tmlr-p6/paper/main.tex:36` is BGE
embeddings + RF/MLP tree ensembles on a synthetic style-classification task (ECE/AUROC/SHAP, N up to 5,000);
`runs/tmlr-tmlr-p9/paper/main.tex:31` is DeepSeek-V4-Pro as executor with GLM5.2 as evaluator, N=5
within-subjects, outcomes are coupling coefficient γ and JSD. Neither produces paired binary verifier decisions,
neither uses `qwen3:4b`, neither has `N=7,f=2`. McNemar's b and c are the off-diagonal cells of **one** 2×2 table
of the **same paired units**; there is no joint pairing here to sum. The volume's own b/c come from a single
synthetic pilot (`paper/main.tex:143` "synthetic pilot, N=7, f=2, n=300 paired per comparison"), so the merge is
rhetorical: nothing in the bundle is a cross-study pooled table, and the caption's "10-seed" pooling is
within-study at best (see MAJOR-2).

**BL-5 — The Theory section proves nothing, contains no theorem to check, and none of its premises exists in the data.**
`paper/main.tex:115-116` (105 words) reads, verbatim: "Assume verifier errors independent, suppose trust denotes
calibration where trust denotes score. Where trust denotes score, sufficient condition for gain is
identifiable flipped verifiers; necessary fails under mimicry. Thus by majority bound we have 0.686 mean;
therefore trust underperforms." Measured over `paper/main.tex` and all three `paper/sections/*.tex` with
`grep -oE "\\label|\\begin"` and specifically `\begin{theorem|lemma|proof|equation|align|definition|algorithm}`:
**zero occurrences of any of them** in the manuscript. `pdftotext` confirms the only uses of "proof(s)" are
claims *about* proofs (`/tmp/render.txt` lines 254, 269, 849, 851). `paper/main.tex:206` promises "Full
1.5-page proofs of Lemma 1 (Kantorovich-Rubinstein), Lemma 2 (non-degeneracy), Theorem (tight min)" in Appendix
K, and Appendix K is an 80-word checklist paragraph with no mathematics. So: (a) no conclusion of any theorem is
stated formally enough to be true or false; (b) the honest-majority premise the whole framing leans on
(`N>3f`, invoked as a citation at `paper/main.tex:40`) is never stated as a condition; (c) it is also **not
recorded anywhere in the data** — `grep -rn "n_verifiers|f_byzantine|honesty" --include=*.json --include=*.jsonl
paper/evidence paper/results` → 0 hits, and `paper/evidence/per_seed_b_c.jsonl` carries only
`seed, condition, b, c, n_d, RD` (field union measured). The regimes the prose claims to cover (mimicry capture,
`0.686` mean majority bound, worst-case `0.32`) are not reached by the data at any precision: `0.686`, `0.32`,
`0.41` are all `NO_CARRIER` (`paper/sections/evidence_inventory.tex:32-36`, plus my census rows for lines 25, 55,
116, 157). A theory section cannot be scored for correctness, and its asserted empirical anchors are uncarried.

**BL-6 — Five of the seven comparison rows in the headline table violate the identities their own columns declare, and the Discussion cites them as results.**
`paper/main.tex:143` states the column contract ("McNemar exact p with continuity-corrected χ²_cc") and admits
the rows below/above the seed block "have **no carrier** in this bundle"; `paper/main.tex:148` prints
`95% CI (Newcombe)`. I recomputed the declared quantities from each row's own b/c (`exact_two_sided` =
2·P(X ≤ min(b,c) | b+c, ½), χ²_cc = (|b−c|−1)²/(b+c)):

| row (line) | b/c | RD printed | (b−c)/300 | χ² printed | χ²_cc / χ²_nocc | p printed | exact p recomputed |
|---|---|---|---|---|---|---|---|
| Historical `:150` | 38/14 | +0.113 | 0.080 | 10.02 | 10.17 / 11.08 | 1.53e-3 | 1.20e-3 |
| Prod shadow `:151` | 36/12 | +0.100 | 0.080 | 9.19 | 11.02 / 12.00 | 5.02e-3 | 7.17e-4 |
| Finance `:156` | 9/4 | +0.167 | (n=30 → 0.167 ✓) | 1.23 | 1.23 ✓ / 1.92 | 0.146 | 0.2668 |
| Mimicry `:157` | 21/18 | −0.090 | +0.010 | 0.10 | 0.10 ✓ / 0.23 | 0.42 | 0.7493 |

Three separate failures. (i) **RD mixes two definitions in one column**: the uncarried rows print the marginal
difference (0.810−0.697 = 0.113, 0.797−0.697 = 0.100, 0.32−0.41 = −0.090) while the seed rows print (b−c)/300 —
for Historical, no n makes both `b/c = 38/14` and `RD = 0.113` true (24/0.113 = 212.4 pairs). (ii) **The Mimicry
row's RD sign contradicts its own b/c**: b=21 > c=18 implies trust *better*, but the row and the abstract
(`:25`) sell it as trust *worse* (0.32 vs 0.41) — the counts are transposed relative to the direction claimed.
(iii) **None of the Finance row's four printed p-variants reproduces**: caption `:143` offers 0.146 two-sided
exact / 0.143 Fisher / 0.083 one-sided / 0.041 mid-p; I compute 0.2668 exact two-sided, 0.1796 mid-p, 0.1334
one-sided, and the asymptotic-with-cc 0.2676 — every printed value is smaller than its recomputed counterpart,
i.e. the "reference" family of four tests on the same 13 discordant pairs is a best-of-4 pick. And `paper/main.tex:168`
cites Historical `p=0.00153` and production shadow `p=0.00502` in the Discussion as findings. The caption's
disclosure is commendable honesty; it does not make the printed numbers usable, and a table whose rows disagree
with their own column contract cannot be the paper's central exhibit.

### MAJOR

**MAJOR-1 — Multiplicity: three mutually inconsistent Holm specifications, and no corrected p anywhere.**
`paper/main.tex:25` says "Holm $k{=}9$"; `:64` says "Holm step-down ($k{=}9$, … $m{=}6,k{=}2$ footnote where
applicable)"; `:143`/`:161` say "Holm $m{=}6,k{=}2$ ($\alpha/(m-k+1)=0.01$)"; `:168` says "Holm $k{=}9$ and
BH-FDR retained". Counting the p-values the volume actually prints (my `grep -oE 'p\{=\}'` pass plus the table
columns): 8 in `tab:f4`'s p column (`:150–157`), 3 further variants of the same Finance contrast (`:143`), the
Wilcoxon at `:161`, 4 in the Discussion at `:168`, 1 Friedman at `:25`, 3 `p_adj` in `tab:full12` (`:211–213`) =
**19 printed p-values over 18 distinct hypotheses**, none of them labelled as adjusted except the three
`p_adj` cells which are themselves `NO_CARRIER` (census lines 211–213). Neither k=9 nor m=6 is the number of
comparisons the paper ran, so the correction denominator is not the experiment's.

**MAJOR-2 — Seven of the ten archived seeds reach no printed number; the choice of subset is unexplained and the statistic is sensitive to it.**
The seeds named in any receipt are `[42, 43, 44]` (I extracted `where.seed` from all 32 rows of
`paper/evidence/CARRIER_RECEIPTS.json`, including nested `inputs`); seeds 45–51 appear in **no** receipt, no
table row and no sentence. Under the pooling rule the paper itself declares, all ten would give `b=151, c=31,
n_d=182, χ²_cc = 77.81, exact p = 3.81e-20` (my computation), versus the printed `44/12, 56, 17.16, 2.09e-5`
(`paper/main.tex:152`). The pooled estimate therefore depends on a 3-of-10 selection with no recorded rule, and
the abstract's "10-seed … provenance" describes the archive, not the analysis. The "missing seed" the brief asks
about is not one but seven, and yes, including them changes the pooled p by ~15 orders of magnitude — which is
precisely why the subset needs a pre-registered justification.

**MAJOR-3 — Two generated body sections now state facts that are false about the run they describe, and the third misreads its own parent document.**
(i) `paper/sections/manifest_audit.tex:31`: "Per-seed JSONL: 0 files with that extension exist anywhere under
the run" — `find . -name '*.jsonl'` now returns `paper/evidence/cells.jsonl` and
`paper/evidence/per_seed_b_c.jsonl`; the section's mtime is 2026-09-26 13:45 vs the carriers' 2026-09-28 14:13.
It directly contradicts the abstract (`:25`) and the artifact inventory (`:14`) on the same page stack.
(ii) `paper/sections/evidence_inventory.tex:13` records `main.pdf` as "341454 B / `6f885cfb59cb5029`"; the live
`paper/main.pdf` is 515345 B / `acb2725a2f87471a…` (my digest table above). The other five rows match byte for
byte, so this is one stale row inside a section whose preamble (`:2`) asserts "every row is a filename, a byte
count, a hash prefix … No value in this section was typed by hand" — a generated section that has not been
regenerated since the PDF it fingerprints was rebuilt.
(iii) `paper/sections/baselines_audit.tex:17-18` and `:29-31`, plus the rendered `figures/fig_baselines.pdf` on
body page 7, present "BFCL 0.95 / WebArena 1.05" as **the accuracies this paper prints**, and build a figure
with an "accuracy ceiling 1.0" line around them (`pdftotext figures/fig_baselines.pdf` shows bars labelled 0.95
and 1.05 under a y-axis named "accuracy"). In `paper/main.tex:133-134` those two numbers are the **GPU-hours**
column: 0.80 + 1.20 + 0.95 + 1.05 = 4.00 = the printed GPU-hours total at `:136`. The manuscript never prints a
BFCL or WebArena accuracy at all. Root cause is a scraping regex, `figures/make_baselines_exhibit.py:34-45`
("The per-family accuracy the manuscript prints", `re.findall(r"(\d\.\d+)\s*&", line)` → `cand[0]`), which
selects whichever two-decimal cell sits before an `&` in the row. A body subsection and a body figure therefore
assert a three-way accuracy discrepancy that is a column misread; the "so that cell cannot be an accuracy
without the quantity being redefined" argument (`baselines_audit.tex:23-25`) is void.

**MAJOR-4 — The Method's reproducibility contract is printed in full and matched by zero artifacts.**
`paper/main.tex:66`: "Every run is described by a `run.json` validated against the schema below", with the
schema at `:68-95` requiring `model`, `temperature`, `seed`, `dataset`, `n_verifiers`, `f_byzantine`,
`honesty_rate`, `attack`, `sha256` and 5 more. `find . -name 'run.json'` → 0 results. The per-seed carrier has
none of those fields (measured field union), so the abstract's "(qwen3:4b, temp0)" attribution
(`:25`), the Table 2 caption's "RTX 4090 ×1 (Ollama qwen3:4b temp0)" (`:125`) and the schema's own `enum` of
three models (`:78`) are not backed by any record of a run. The two model names in that enum (`qwen2.5-7b`,
`qwen2.5-1.5b`) are also what the census's decimal extractor picked up as `2.5`/`1.5` and "carried" by reviewer
risk scores — see MINOR-1.

**MAJOR-5 — The 18,000-trial / 6 GB / 2700-holds / 192-144-90-40 scale claims have no per-observation record.**
`paper/main.tex:121` and `:125` and `:182`. The table at `:131-136` is internally additive (I checked:
4000+5000+4500+4500 = 18,000; 0.80+1.20+0.95+1.05 = 4.00; 1.2+1.8+1.5+1.5 = 6.0), so the arithmetic is sound and
the provenance is not: my numeric-leaf scan over every JSON in the run finds no leaf with the value 192, 144,
2700 or 18000 in any quantity role (40 appears only as `real40.json#n_total`, 300 only as the derived table's
`n_paired`, both different quantities). The run's own register agrees (`evidence_inventory.tex:26-46`: 0 of 11
headline numbers have a carrier). Additionally the only multi-seed record file that does exist,
`paper/results/analysis.json:18`, self-declares `"source": "local_270_synthetic_cloud_aligned"`, and
`baselines_audit.tex:34-36` reads that as "a synthetic alignment rather than 270 real trials" — so the file that
supplies the second "10 seeds" (`n_seeds: 10`, seeds 0–9 in `cells.jsonl`, measured) is disclaimed as simulated
in the same paper that prints "10-seed cloud provenance".

**MAJOR-6 — Structural defects a referee sees immediately.** (a) The central results table `tab:f4`
(`paper/main.tex:144`) is **never referenced** from the text, nor is `tab:full12` (`:212`) or
`sec:evidenceinventory` — measured by set difference over all four `.tex` files. (b) Gate counts disagree:
"10/10 gates passing" (`:121`), "10/10" in every row and the total of Table 2 (`:131-136`), caption "10/10
gates" (`:125`), versus "Gates 9/9" (`:182`) — with no `gates_history` file to settle it (`manifest_audit.tex:31`,
and my `find`). (c) `paper/main.tex:113` still prints the pooled statistics the caption declares corrected —
"$n_d{=}55$, $b{=}44,c{=}11$ … $p{=}8.69\times10^{-6}$ … $\chi^2{=}18.62$" — contradicting `:152`
(56, 44/12, 2.09e-5, 17.16) on the same page, and `:161` then prints a third value "Wilcoxon
$p{=}8.60\times10^{-6}$" for what it calls an "equivalence with McNemar". The rewrite script's own guard
(`.aris/f4_table2_seed_rows.py:150`) only tested the four seed **rows**, so the stale numbers in the prose
survived. (d) `paper/main.tex:113` is additionally a spliced sentence: "…is not plotted: no file in the archive
records the sweep Single-generator seed~42 sensitivity is reported with pooled SD 0.026…" — two sentences fused
mid-clause with no punctuation. (e) `paper/main.tex:148` still labels the interval column "95% CI (Newcombe)"
while the caption at `:143` states the interval "is now a Wald interval".

**MAJOR-7 — The "Extended Main Text for 12-page Journal Version" section is a page budget, not substance, and its one table contradicts §5.**
`paper/main.tex:208-209` (161 words including its table) describes planned additions — "We add 1 page to Related
Work … 0.5 page to Method (formal definitions of Γ, σ²_b with pseudocode Algorithm~1) … This adds ≈600 words and
2 tables/1 figure, pushing total from 8 to 12 pages". Measured against the document: it contains 1 table and 0
figures (not "2 tables/1 figure"), no Algorithm environment exists anywhere (`grep -n "Algorithm" paper/main.tex`
→ the only hit is the promise at `:209`), and the rendered total is 12 pages (`pdfinfo`) with a body of 8.67 —
so "7 to 12 pages" describes neither instrument. Its table `tab:full12` (`:211`) is titled "Per-task
per-channel per-seed **full** stats (500 paired, Qwen3:4b)" and prints 3 rows, while `paper/main.tex:165`
states "The per-task, per-channel, per-seed breakdown … **is not reported here**". Every number in it is
`NO_CARRIER` except two accidents (`0.015` screened by `rows.43.ci_lo = 0.01486`, `0.014` by
`rows.44.se_RD = 0.01414`; census rows for lines 212–213). Substance versus volume: this section, plus appendices
I/J/K at 132/103/96 words, is the padding — and as noted it is excluded from the floor measurement anyway, so it
buys no pages on the instrument that counts.

### MINOR

**MINOR-1 — Every one of the 33 SCREEN_ONLY rows is an accident, and the screen's leaf pool includes the author's own review verdicts.** I opened all 33 bases.
Representative: `2.5` at `:78`/`:100` and `1.5` at `:78`,`:133`,`:134`,`:191`,`:192`,`:201`,`:206` matched to
`source/reviews/ten_review_cloud_R902.json#risk.risk (=2.5)` and `ten_review_sim_R901.json#risk.risk (=1.5)` —
reviewer risk scores matching digits inside the model name `qwen2.5-7b`, the GPU-hours cells, and the phrase
"1.5 pages"; `4.00` (total GPU-hours, `:136`) matched to `f4_table2_seed_rows.json#rows.44.c (=4)` (a discordant
count); `6.0` (GB, `:136`) to `REPRO_CLAIMS.json#protocol_search_strings.keyword_clusters_in_review (=6)`;
`0.1` at `:116`,`:151`,`:157`,`:206` to `rows.42.p_exact = 0.063568` rounded at dp=1; `0.01` at `:143`,`:161` to
`se_RD = 0.01453` at dp=2; `0.5` at `:209` to `grid_results[0].gamma = 0.5`. None is the same quantity; several
are the same *file* whose values BL-2 shows are not re-executed. Two instrument observations follow, filed here
rather than as criticisms of the paper: the screen rounds a leaf to the printed dp (so any leaf within half a
unit in the last place "carries" anything), and it treats `source/reviews/*.json` as data although those are
testimony about the manuscript — the mirror detector in `paper/EVIDENCE_RECORD.md:29` reports 0 mirror-lean
because the review files do not *declare* they were extracted from `main.tex`.

**MINOR-2 — `evidence_manifest.json:2` gives `root` as `F:\Research\MERGED_FLAGSHIPS\F4_Verification` while
`CUSTOM_REQUIREMENTS.md:3` says the ingest came from `/data3/Research/MERGED_FLAGSHIPS/F4_Verification`;** the
manifest lists 32 entries of which 31 carry a `sha256` (measured), and `paper/main.tex:182` still says the list
was "overstated" without giving the corrected number, while `:179` calls it "120 fingerprinted SHA256".

**MINOR-3 — `paper/CLAIM_LEDGER.md` ships a single row** (`C01 | n=90 seed=3 P_mean 0.2502 |
results/analysis.json | PASS`) whose stated values contradict the carrier it names (`analysis.json` says
`n_cells=270, n_seeds=10, P_mean=0.2493`), marked PASS; `paper/claims.yaml:3-5` documents the conflict and lists
4 claims total (C01–C04). The abstract's "All claims use a claim-ledger" (`:25`) is thus a 4-claim ledger over a
manuscript that prints 165 decimal occurrences.

**MINOR-4 — `paper/evidence/protocol.md` is 3 lines / 145 bytes** (measured: "Protocol F4_Verification / Dataset:
synthetic, license CC-BY-4.0, source local. / Compute: Ollama qwen3:4b temp0, GPU RTX 4090 x1, runtime 4h."), yet
it is cited as the anchor for the six-factor thresholds (`:113` "protocol.md Table~1, §2"), for GPU cost
(`:121`, `:125`), and for the search-string claim the paper later withdraws (`:182`). There is no Table 1 in it.

**MINOR-5 — Appendix J (`:202`) prints parse rates 98.2/93.3/99.1% and ECE/NLL/Brier/AUROC values (0.228, 0.1139,
0.1832, −0.037, 0.99) that are all `NO_CARRIER` (census lines for `:202`), in the same paragraph that concedes the
curves are withdrawn.**

## Score table (1–10, TMLR scale)

| dimension | score | one-line justification |
|---|---|---|
| novelty / significance | 2 | Verification under capture is a real question, but the "six-study volume" merge names four studies that do not exist on disk and the two that do share no design (BL-4), so no merged contribution is identifiable. |
| soundness of experiments | 2 | The headline pooled RD is 3× its own components and its CI excludes the correct value (BL-1); 5 of 7 table rows break their declared identities (BL-6); 7 of 10 seeds never enter an estimate (MAJOR-2); 19 printed p-values with three conflicting Holm denominators and no corrected value (MAJOR-1). |
| reproducibility | 4 | Genuinely re-executable machinery exists and I re-ran it clean (census reproduces 106/165/19/33/0/113; receipts PASS=32; page instrument locates its boundary), and the manifest audit is real work — but the schema promising per-run metadata has zero instances (MAJOR-4), the derived table has no regeneration path (BL-2), and two generated sections now assert false facts (MAJOR-3). |
| claims / evidence match | 1 | The abstract asserts a test the body withdraws (BL-3), a "0.686 mean majority bound" and mimicry figures with no carrier and no theorem (BL-5), "full proofs" in an appendix containing no mathematics (0 theorem/proof/equation environments measured), and a breakdown table that §5 says is not reported (MAJOR-7); 113/165 printed decimals carry nothing. |
| writing quality | 2 | A sentence spliced mid-clause (`:113`), the central table never cross-referenced, two gate counts, two interval names for one column, a section titled as a page budget, and prose in Theory that is not compositional English (BL-5). |

## Decision

**BLOCKED.** 6 BLOCKING, 7 MAJOR, 5 MINOR. The manuscript's own apparatus is the reason: the receipts gate
reports `PASS=32 FAIL=0` and the census reports `CARRIER 19`, and both are true, while the pooled estimate on the
page is 3× wrong (BL-1), the point estimates and intervals that the reader is asked to believe are certified by
transcription rather than re-execution (BL-2, proven by mutation), and the abstract asserts a statistic the body
has already withdrawn (BL-3). A clean gate reading is not evidence here, and the fix order is: (i) correct the
pooled denominator and re-derive the seed block end-to-end from the raw carrier with the derived table regenerated
by the same command that verifies it; (ii) re-scope the merge claim to the studies that exist and state why
cross-study McNemar pooling is or is not performed; (iii) delete or fully re-issue the abstract's withdrawn
Friedman/Nemenyi sentence; (iv) either write the theory (statements, premises, proofs) or remove the section and
its numeric attribution; (v) rebuild rows `:150-151`, `:156-157` or drop them; (vi) regenerate
`sections/*.tex` against the current tree and re-point `body_pages`/`page_standard` afterwards.

### Commands I re-ran

    cd /home/liuzewen/Projects/agi-paper-pipeline
    # integrity, open and close (digests above)
    python3 -c "import hashlib,os;[print(f,hashlib.sha256(open(f,'rb').read()).hexdigest()) for f in \
      ['runs/tmlr-f4-verification/paper/main.tex','runs/tmlr-f4-verification/paper/main.pdf','runs/tmlr-f4-verification/paper/evidence/CARRIER_RECEIPTS.json']]"
    # copies for every mutating step
    python3 -c "import shutil;[shutil.copytree('runs/tmlr-f4-verification',d,symlinks=True) for d in ('/tmp/f4r1_live','/tmp/f4r1_mut')]"
    find runs/tmlr-f4-verification -type l | wc -l                              # 0
    # seed count (the headline measurement)
    cd runs/tmlr-f4-verification/paper/evidence && wc -l per_seed_b_c.jsonl     # 9  <- newline count, NOT records
    python3 -c "import json;rs=[json.loads(l) for l in open('per_seed_b_c.jsonl').read().splitlines() if l.strip()];print(len(rs),len(set(r['seed'] for r in rs)))"   # 10 10
    python3 -c "b=open('per_seed_b_c.jsonl','rb').read();print(len(b),b.count(b'\n'),b.count(b'\r\n'),b.endswith(b'\n'))"   # 782 9 9 False
    # receipts, live copy and mutated copy
    python3 tools/carrier_receipts.py --run /tmp/f4r1_live                     # PASS=32 FAIL=0 NOT_VERIFIABLE=0 (rc 0)
    python3 tools/carrier_receipts.py --run /tmp/f4r1_mut                      # PASS=25 FAIL=7 (rc 1), rows listed in BL-2
    # census, both copies
    python3 tools/manuscript_literal_census.py --run /tmp/f4r1_live            # 106/165 CARRIER 19 SCREEN_ONLY 33 ASSERTED_NOT_RUN 0 NO_CARRIER 113
    python3 tools/manuscript_literal_census.py --run /tmp/f4r1_mut             # CARRIER 16 / SCREEN_ONLY 36 (moves)
    python3 tools/manuscript_literal_census.py --run /tmp/f4r1_live --json /tmp/census_live.json
    # independent recomputation of the derived table + pooling arithmetic (BL-1, MAJOR-2): stdlib script, 0 mismatches vs baked file,
    #   3-seed pooled RD 0.10667 = 3.002 x mean single-seed RD; honest 32/900 = 0.0356 CI [0.019,0.052]; all-10 b=151 c=31 n_d=182 chi2=77.81 p=3.81e-20
    #   (BL-6): exact two-sided / mid-p / chi2_cc recomputation for rows :150,:151,:156,:157
    grep -rln "f4_table2_seed_rows" gates/ tools/ tests/                       # no output
    find runs/tmlr-f4-verification -name 'run.json'                            # no output
    find runs/tmlr-f4-verification -name '*.jsonl'                             # cells.jsonl, per_seed_b_c.jsonl
    grep -rn "n_verifiers\|f_byzantine\|honesty" --include=*.json --include=*.jsonl paper/evidence paper/results   # no output
    ls runs/ | grep -Ei 'p(6|9|10|11|12|13|14)'                                # p9-pilot, tmlr-tmlr-p12, tmlr-tmlr-p6, tmlr-tmlr-p9
    ls -d runs/tmlr-tmlr-p12/paper                                             # absent
    # LaTeX: build, log, references
    cd /tmp/f4r1_live/paper && xelatex -interaction=nonstopmode -halt-on-error main.tex && bibtex main && xelatex main.tex && xelatex main.tex && xelatex main.tex
    grep -c "^!" /tmp/build1.log /tmp/build2.log /tmp/build3.log /tmp/build4.log   # 0 each
    grep -n "undefined\|LaTeX Warning" main.log                                     # 0 hits
    pdfinfo main.pdf | grep Pages                                                    # 12
    grep -c "bibitem" main.bbl ; grep -c "^@" paper/refs.bib                        # 42 / 42
    grep -o "\\label{[^}]*}" paper/main.tex paper/sections/*.tex | sort -u          # unreferenced: tab:f4, tab:full12, sec:evidenceinventory
    grep -oE "\\\\begin\{(proof|theorem|lemma|equation|align|definition|algorithm)" paper/main.tex paper/sections/*.tex   # 0 hits
    pdftotext /tmp/f4r1_live/paper/main.pdf /tmp/render.txt ; pdftotext figures/fig_baselines.pdf -
    # length instruments (read-only; tree digest unchanged afterwards)
    python3 tools/body_pages.py runs/tmlr-f4-verification                          # body=8.67 total=12 ends p9 frac 0.67 [appendix]
    python3 gates/page_standard.py --root runs/tmlr-f4-verification                # PASS, floor 8, ceiling none

### NOT_ASSESSED

1. Whether per-observation records for the 18,000 trials, the 6 GB store, the 192/144/90/40 splits, the 2700
   tightness holds or the 10/10 gates exist anywhere off this machine (`/data3/...` and `F:\...` are not mounted;
   absence here is not proof of absence). Not a criticism, an unreachable input.
2. Whether the seven unused seeds (45–51) are the same 300 paired units as 42–44 or independent samples: the
   carrier records no pair IDs, so neither the correct pooled variance nor whether the pooled exact test is
   admissible can be decided from shipped data. Marked NOT_VERIFIABLE by design, not scored.
3. The truth or falsity of any Theory claim: with no statement, premise or proof in the manuscript (BL-5), there
   is nothing to check; I assessed only the absence of the artifact, not the mathematics.
4. External validity of the 42-paper survey (whether each cited paper says what `:36`, `:38`, `:40`, `:61` claim),
   PRISMA funnel numbers 216→142→68→42, and JCR/CCF Q1 status of the exemplars: no bibliographic network or
   credential used in this review. I verified only that `refs.bib` has 42 entries and all resolve in the build.
5. Whether `100_suggestions.md`/`.pdf`, `GANTT_500_5d.md`, `PAPER_IMPROVEMENT_LOG.md`, `REVISION_LOG_B.md`,
   `100_suggestions_checked.md` bear on any printed claim: they are process documents and I did not treat them as
   evidence either way.
6. Whether the earlier `b1-evidence-20260926T181543Z-01` verdict (a different tier, `verdict=FAIL`, receipts total
   0 at that time) was subsequently discharged: I read its header for context only; this round's findings stand on
   today's bytes.
7. Reproduction of the Wilcoxon `8.60e-6` (`:161`) and the `d_z`, CLES, `p_adj`, bootstrap-B=5000 values: no
   per-observation input in the bundle from which to recompute them (they are `NO_CARRIER`, but the reason is an
   absent input rather than a demonstrated wrong number, so I record NOT_ASSESSED for the number itself).
8. Anonymity compliance and TMLR form fit beyond what `tools/audit_tmlr_submission_form.py`-style gates cover; I
   checked only that the PDF builds with `tmlr.sty` and carries an anonymous author block (`paper/main.tex:21`).
