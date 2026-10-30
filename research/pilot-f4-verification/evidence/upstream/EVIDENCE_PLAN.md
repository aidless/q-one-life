# EVIDENCE_PLAN — tmlr-f4-verification

Dispatch handle: `b1w2-tmlr-f4-verification-20260926T181543Z`
Live tree: `paper/` (`live_manuscript` = `runs/tmlr-f4-verification/paper/main.tex`), so evidence was
staged under `paper/evidence/` per WAVE.md deliverable 2.
Screen input: 73 reported numbers, 20 flagged unbacked (`inventory/carrierless_claims.json`, this run's entry).
Receipt measurement: `python3 tools/carrier_receipts.py --run runs/tmlr-f4-verification`
→ `tmlr-f4-verification: PASS=0 FAIL=0 NOT_VERIFIABLE=0 (total 0)`

**Result up front: 0 of the 20 screen-flagged numbers earned a PASS receipt.** No row was written
that I could not honestly claim is carried. The reasons are per-number below, and the two structural
blockers (one in the archive, one in the receipt schema) are in the last two sections.

## Staged artifacts

Copied byte-for-byte from the read-only source project `/data3/Research/MERGED_FLAGSHIPS/F4_Verification`;
the source project was not written to (mtimes unchanged).

| staged file | sha256 (first 16) | source path | what it is |
|---|---|---|---|
| `paper/evidence/per_seed_b_c.jsonl` | `ae825d152bb49c0b` | `evidence/per_seed_b_c.jsonl` | per-seed McNemar discordant counts `b`,`c`,`n_d`,`RD`, seeds 42–51 (10 records) |
| `paper/evidence/cells.jsonl` | `254d9c6c7ca7e749` | `results/cells.jsonl` | 270 raw grid records `{seed, cell, P_mean}` |

Why these two and only these: they are the **only** machine-readable experiment records that exist in the
source project and are absent from the run. The other four primary files (`evidence/baselines/baselines.json`,
`evidence/baselines/real40.json`, `results/analysis.json`, `evidence/protocol.md`) are already in the run
tree and byte-identical to the source project (verified by `sha256sum`: `be6f0c999b6de8a9`, `35b3cbdfda20c0a7`,
`565c5822a20700bc`, `fbe6caea4a7ed10d`), so re-copying them would add nothing.

Side effect worth noting: `paper/main.tex:143` cites `evidence/per_seed_b_c.jsonl` by name, and that path did
**not** resolve anywhere in the run before this wave. Staging it repairs a dangling artifact citation. It does
not carry any flagged number (see below).

## Per-number table

Line numbers are in the live manuscript `paper/main.tex`.

| # | value | line(s) | what the paper says it is | carrier status | receipt row | reason class |
|---|---|---|---|---|---|---|
| 1 | `0.00153` | 168 | exact McNemar p, Historical 38/14/52 | not carried | none | STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA |
| 2 | `0.1139` | 202 | Brier score | not carried | none | NO_PRIMARY_SUBSTRATE |
| 3 | `0.1832` | 202 | ECE | not carried | none | NO_PRIMARY_SUBSTRATE |
| 4 | `0.686` | 25, 116 | mean majority bound (theory) | not carried | none | NO_PRIMARY_SUBSTRATE |
| 5 | `0.697` | 150, 151, 168 | majority-arm accuracy | not carried | none | NO_PRIMARY_SUBSTRATE |
| 6 | `0.797` | 113, 151, 168 | production-shadow arm accuracy | not carried | none | NO_PRIMARY_SUBSTRATE |
| 7 | `0.810` | 113, 150, 168 | historical arm accuracy | not carried | none | NO_PRIMARY_SUBSTRATE |
| 8 | `10.02` | 150 | continuity-corrected McNemar χ² | not carried | none | STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA |
| 9 | `16.86` | 154 | χ²_cc, single seed 43 | not carried | none | STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA |
| 10 | `18.62` | 113, 152, 153 | χ²_cc, seeds 42/43/44 pooled | not carried | none | STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA |
| 11 | `2.76` | 168 | Holm p (×10⁻⁸), skill capital +0.110 | not carried | none | NO_PRIMARY_SUBSTRATE |
| 12 | `3.02` | 154 | exact p (×10⁻⁶), single seed 43 | not carried | none | STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA |
| 13 | `4.00` | 136 | total GPU-hours (sum of the column above) | not carried | none | PROSE_ANCHOR_ONLY |
| 14 | `5.02` | 151 | exact p (×10⁻³), production shadow | not carried | none | STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA |
| 15 | `5.45` | 168 | Holm p (×10⁻⁶), claim graph +0.073 | not carried | none | NO_PRIMARY_SUBSTRATE |
| 16 | `6.70` | 155 | χ²_cc, single seed 44 | not carried | none | STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA |
| 17 | `8.60` | 161 | Wilcoxon p (×10⁻⁶) | not carried | none | NO_PRIMARY_SUBSTRATE |
| 18 | `8.69` | 113, 152, 153 | exact p (×10⁻⁶), pooled 42/43/44 | not carried | none | STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA |
| 19 | `9.19` | 151 | χ²_cc, production shadow | not carried | none | STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA |
| 20 | `9.40` | 155 | exact p (×10⁻³), single seed 44 | not carried | none | STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA |

Reason-class totals: STATISTIC_NOT_EXPRESSIBLE_IN_SCHEMA 10, NO_PRIMARY_SUBSTRATE 9, PROSE_ANCHOR_ONLY 1.
Sub-set note: 8 of the 10 schema-blocked rows are **also** contradicted by primary or by the table's own
arithmetic (rows 8, 9, 10, 12, 14, 16, 18, 19 in this table plus `0.00153`), itemised below.

## What I searched, and where

1. **Every machine-readable file in the source project.** Full `find` of
   `/data3/Research/MERGED_FLAGSHIPS/F4_Verification` (781,507 bytes, 78 files): the only experiment
   records are `evidence/per_seed_b_c.jsonl`, `results/cells.jsonl`, `results/analysis.json`,
   `evidence/baselines/baselines.json`, `evidence/baselines/real40.json`. The 41 `reviews/*.json` are
   LLM-review logs (`score`, `verdict`, `elapsed_s`) — process metadata, not observations.
   `evidence_manifest.json` / `MANIFEST_ingest.json` are file indexes.
2. **Every JSON/JSONL in the run tree** (`runs/tmlr-f4-verification`, excluding `backups`), 107 files
   across both roots.
3. **Numeric-leaf match, not substring match.** I walked the parsed structures and compared *numeric
   leaves* against each flagged value at print precision, rather than grepping digits. This matters:
   a first pass that regex-scanned string content reported spurious hits for `2.76`, `3.02`, `5.45`,
   `8.60`, `8.69` and `4.00` coming out of SHA256 hex fields in the two manifests. Those are digit
   collisions, not carriers, and the `quantity` field in the receipt schema exists exactly to refuse them.
4. **Every `op` the schema can execute.** For all 5 primary files I enumerated all 890 numeric scalar
   leaves (locator candidates) and all 11 numeric arrays plus per-column record arrays
   (`mean|median|sum|min|max|std|n` candidates) and compared against all 20 values.
   Result: 19 of 20 produce **zero** candidate matches. The 20th, `4.00`, produces 40 matches that are all
   `per_seed_b_c.jsonl → c = 4` (a McNemar discordant count) and `cells.jsonl → cell = 4` (a cell index) —
   right digits, different quantity. I did not write those rows; pointing a GPU-hours claim at a discordant
   count is bending the locator to make a row pass.
5. **The supplementary package.** `paper/supplementary_tmlr-f4-verification.zip` (md5 `cbad02b0a2a0435c927e29046645fc41`,
   identical to the `source/` copy) contains 4 members totalling 1,099 bytes: `evidence/baselines/baselines.json`,
   `evidence/baselines/real40.json`, `evidence/protocol.md`, `results/analysis.json`. `find` cannot see inside a
   zip, so this was opened explicitly: no per-observation record is hidden there, and neither newly staged
   raw file is shipped in it.
6. **Text/prose occurrences** across the run tree with context printing. Every value appears only in
   (a) `main.tex` / `main_full.tex` (the manuscript quoting itself), (b) planning notes
   (`100_suggestions*.md`, `GANTT_500_5d.md`, `LITERATURE_REVIEW.md`) that restate the manuscript, or
   (c) audit prose derived from the manuscript (`REVIEW_CARD.md`, `reports/hallucination.md`). The run's own
   generated register `paper/sections/evidence_inventory.tex:36` and `figures/EVIDENCE_RECORD.md:91` already
   record `0.686` and `4.00` as `NO_CARRIER`, and state the exclusion rule this wave respects: a value copied
   out of `main.tex` cannot certify `main.tex`.

## What is missing, per number

- **`0.810`, `0.797`, `0.697`** — need per-item outcome records for the three arms (`n = 300` paired, IDs
  `hist-001..300`, `prod-001..300` per `paper/main.tex:143`). No item-level file exists in either tree. With
  such a file the schema *could* express these as `op: mean, over: items[*].correct`. `paper/main.tex:25` and
  `:64` promise "per-seed JSONL archived"; `figures/REPRO_CLAIMS.json` records `per_seed_jsonl.files_found: []`.
- **`0.1139`, `0.1832`** — Brier/ECE need per-observation `(predicted, label)` pairs. The manuscript concedes
  this itself at `paper/main.tex:177` ("the ECE and Brier values quoted in the text have no per-observation
  record in the archive").
- **`2.76×10⁻⁸`, `5.45×10⁻⁶`, `8.60×10⁻⁶`** — Holm/Wilcoxon p for the skill-capital, claim-graph and
  paired-binary ablations. No ablation observation records exist; `paper/main.tex:161` attributes the
  `mean(d) == 0.110` assert to a "single script" that is not in the archive (the run has 0 archived scripts;
  `paper/sections/evidence_inventory.tex` artifact-class line says `script: 0`).
- **`0.686`** — theory quantity ("mean majority bound"); would need the per-study majority bounds it averages.
  Not archived anywhere; already `NO_CARRIER` in the generated register.
- **`4.00`** — the total GPU-hours column sum. Its four addends (0.80/1.20/0.95/1.05, `paper/main.tex:131–134`)
  exist in no file. The nearest anchor is prose: `paper/evidence/protocol.md:3` "runtime 4h", which the
  manuscript also cites at `paper/main.tex:121`. That is a *total*, stated in three lines of markdown with no
  machine-readable field and no per-family split, so it is a prose anchor rather than a carrier — no row written.
- **`0.00153`, `10.02`, `9.19`, `18.62`, `16.86`, `6.70`, `8.69`, `3.02`, `5.02`, `9.40`** — see next section.

## Two structural blockers (why no row was written for the Table 4 statistics)

**1. The receipt schema cannot express these statistics.** Every one of the ten is a function of *two*
fields of a dichotomy table — χ²_cc = (|b−c|−1|)²/(b+c) and the exact McNemar binomial tail — not a literal
field and not a single-array reduce. The schema offers `locator` (a named field equal to the value) or
`op ∈ {mean, median, sum, min, max, std, n}` over one array path. There is no bivariate form, so these rows
cannot be written at all. Per WAVE.md, they are left out rather than bent.

**2. The one primary record for those rows is JSONL, which the tool refuses.** I confirmed this by executing
a receipt row against `paper/evidence/per_seed_b_c.jsonl`; the tool printed
`NOT_VERIFIABLE … artifact is not JSON: paper/evidence/per_seed_b_c.jsonl`. So even a per-seed record whose
values matched the table could not be receipted through this instrument.

To be explicit that the blockers are properties of the archive and the schema — not of my wiring — I ran a
capability probe with a genuinely recomputable row (`op: mean` over `grid_results[*].P_mean` in
`paper/results/analysis.json`), which returned **PASS**. The same probe with a nonexistent artifact returned
`NOT_VERIFIABLE … artifact not on disk`. Both probes were transient; the ledger was restored to `[]` before
the final tally quoted above. So the instrument does read `paper/evidence/CARRIER_RECEIPTS.json`, does execute
rows, and does PASS a real derivation — and 0 of 20 flagged numbers survive it.

## Contradictions found while looking for carriers

Re-derived from the table's own stated `b`/`c` (exact two-sided binomial, continuity-corrected χ²), and from
the staged primary `paper/evidence/per_seed_b_c.jsonl`:

| paper row | printed χ²_cc | χ²_cc from printed b/c | printed exact p | exact p from printed b/c |
|---|---|---|---|---|
| `paper/main.tex:150` 38/14, n_d 52 | 10.02 | 10.17 | 1.53×10⁻³ | 1.20×10⁻³ |
| `paper/main.tex:151` 36/12, n_d 48 | 9.19 | 11.02 | 5.02×10⁻³ | 7.17×10⁻⁴ |
| `paper/main.tex:152/153` 44/11, n_d 55 | 18.62 | 18.62 ✓ | 8.69×10⁻⁶ | 8.70×10⁻⁶ ✓ |
| `paper/main.tex:154` 41/10, n_d 51 | 16.86 | 17.65 | 3.02×10⁻⁶ | 1.47×10⁻⁵ |
| `paper/main.tex:155` 31/9, n_d 40 | 6.70 | 11.03 | 9.40×10⁻³ | 6.80×10⁻⁴ |

Against the staged primary record (seeds 42+43+44 pooled = b 44, c 12, n_d 56 → χ²_cc 17.16, exact p 2.09×10⁻⁵;
per-seed 42 = 14/5/19, 43 = 16/3/19, 44 = 14/4/18), the table's `44/11`, `41/10`, `31/9` and `n_d` 55/51/40
are roughly 3× too large, and the printed pooled RD (+0.110) is 3× the primary pooled mean RD (0.0355).
`paper/main.tex:150/151`'s RD column (+0.113, +0.100) equals the *arm-rate* difference (0.810−0.697, 0.797−0.697),
not (b−c)/300 = 0.080 — so one table row mixes two denominators. These are the reason no honest derivation
lands on the printed values; recording the printed numbers as "carried" would launder them.

## Checked and sound (no flagged number here)

The staged `paper/evidence/cells.jsonl` does re-derive `paper/results/analysis.json` in full:
270 records (= `n_cells`), 10 distinct seeds (= `n_seeds`), mean `P_mean` = 0.249278 → 0.2493,
population SD = 0.028931 → 0.0289 (= `P_std`; ddof=1 would give 0.0290, so the archived convention is
population SD), and normal-approx interval [0.2458, 0.2527] = `P_CI95`. That supports `claims.yaml` C01–C04,
none of which is on the screen's flagged list, so it earns no row here.

## Adjacent observations (not receipted, not part of the flagged 20)

- `paper/main.tex:179` promises "Per-seed JSONL" and "`evidence_manifest.json` 120 fingerprinted SHA256".
  The manifest declares **32** paths (`figures/MANIFEST_AUDIT.json`: `entries: 32`, `match 19 / mismatch 7 /
  absent 5 / no-hash-field 1`) and **none** of them is a `.jsonl` or `.csv`: the fingerprint list indexes the
  manuscript and build outputs, never an experiment record. So the missing substrate is not only unpublished —
  it was never inside the archive's own integrity envelope.
- The 5 `absent` manifest entries are all `main_full.*` build files; no experimental file was lost to drift.

## Honest bottom line

0 of 20 flagged numbers placed. Fewer than half, by a wide margin, and the gap is not closable by staging:
it needs the per-item and per-observation experiment records (`hist-*`/`prod-*` outcome JSONL, calibration
`predicted,label` pairs, ablation observations, per-study majority bounds), none of which exists in
`/data3/Research/MERGED_FLAGSHIPS/F4_Verification` or in this run. Additionally, the ten McNemar-family
statistics need a bivariate derivation the receipt schema does not have, and the tool will not read JSONL
artifacts at all.
