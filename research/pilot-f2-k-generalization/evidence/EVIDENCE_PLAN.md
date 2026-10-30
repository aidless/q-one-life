# EVIDENCE_PLAN — tmlr-f2-theory (wave b1w4, handle `b1w4-tmlr-f2-theory-20260927T034219Z`)

Live tree: `paper/` (live manuscript `paper/main.tex`, 276 lines), so evidence lives at
`paper/evidence/` and receipts at `paper/evidence/CARRIER_RECEIPTS.json`
(`tools/carrier_receipts.py` resolves `source/evidence/CARRIER_RECEIPTS.json` to this
sibling path). Instrument run:
`python3 tools/carrier_receipts.py --run runs/tmlr-f2-theory`.

Screen flagged 7 values (`inventory/carrierless_claims.json`, entry `tmlr-f2-theory`,
63 reported / 7 unbacked). **Placed as executable receipts: 0 of 7. The receipts file is
an empty array on purpose: every candidate derivation for those 7 is either an author's
accounting entry, prose in a file the instrument cannot load, or a statistic whose
per-item inputs were never archived.** No number below is claimed carried.

## Per-number table

| value | line(s) | what the sentence claims | disposition | reason class |
|---|---|---|---|---|
| `0.1139` | `paper/main.tex:45` | Brier score of the p16 CIFAR calibration whose reversal vs ECE motivates the row | NOT PLACED | per-item outcomes never archived |
| `0.1832` | `paper/main.tex:45` | ECE of the same run (binning-bias comparator) | NOT PLACED | per-item outcomes never archived |
| `0.686` | `paper/main.tex:24,47,136,241` | worst-case error of the analytic $f{=}2$ counterexample | NOT PLACED | carrier is prose in a `.md`; asserted construction, not a measurement |
| `0.797` | `paper/main.tex:124` | declared six-factor threshold pair, "in `evidence/protocol.md` Table 1" | NOT PLACED | named carrier does not contain it (false pointer) |
| `0.810` | `paper/main.tex:124` | same | NOT PLACED | same |
| `3.84` | `paper/main.tex:24,184,190` | total GPU-hours = sum of the four family rows | NOT PLACED | author's accounting; no `gpu_hours` field in any artifact; a table is not its own carrier |
| `4.84` | `paper/main.tex:239` | explicitly quoted as an earlier draft's value with **no** carrier | NOT PLACED (correctly) | withdrawn value; receipting it would contradict the sentence |

## What I searched, and what is missing

Searches are literal `grep -rn` over (a) the whole run tree excluding `.backups`/`backups`,
all file types, and (b) the authorized source project `/data3/Research/MERGED_FLAGSHIPS/F2_Theory`
(15 evidence files, 108 KiB). JSON/JSONL/YAML/CSV-only variants were run separately. I did
**not** search outside those two roots, so "absent" below means "absent from the authorized
scope", not "does not exist".

- **0.1139 / 0.1832** — 18 files in the run tree contain the literals; every one is either the
  manuscript line itself (`paper/main.tex`, `source/main.tex`), the suggestion list
  (`100_suggestions.md:71`, `100_suggestions_checked.md:83`), a scanner dump of the
  manuscript's own numeric literals (`reports/hallucination*.md`, `reports/ledger*.md` line 19),
  or a review paste. Zero data files. In the source project the only non-`.tex` hits are those
  same suggestion/report files. What is missing: the p16 calibration archive (per-class
  probabilities or the 15-bin histogram + counts that ECE and Brier are sums over).
  `paper/evidence/p16_provenance.json` carries only `model/temp/seeds/total_cells=300/
  provenance/generated/note` — no calibration fields, so it cannot support either number
  (it is also the file the row's own cell names as if it did).
- **0.686** — the *only* carrier in either root is `paper/evidence/tightness_proof.md:8`
  ("Construct worst-case f=2 captured counterexample (error 0.686)"). `load_artifact()` in
  the instrument accepts `.json/.jsonl/.ndjson/.csv` only, so a markdown proof sketch cannot
  be executed even in principle. Zero hits in any JSON/JSONL/YAML/CSV in either root (the
  three `686` substrings inside JSONs are SHA-256 hex fragments and a `prompt_tokens` count).
  No script in either root computes it. Class: analytic worst case asserted at one decimal
  place — reporting it needs the construction, not an archive.
- **0.797 / 0.810** — `paper/evidence/protocol.md` is 219 B / 4 lines (`# Protocol F2`, the
  2700-cell line, a dataset line, `Compute: Ollama qwen3:4b, 32GB, seed 42.`). It has no
  table and none of `$H\ge0.85$`, `coverage\ge0.90`, `0.810`, `0.797`, `w_c=50`, `violations 0`,
  `takeover 0.00` (grep for those 7 patterns: 0 hits). The only other place the pair occurs is
  `paper/100_suggestions.md:55,57` (and its `_checked` twin, item ticked ✅), where they are
  *rates*: "Historical 0.810 vs 0.697 p=0.00153" and "Production shadow 0.797 vs 0.697
  p=0.00502". The comparator `0.697` occurs nowhere in either root outside those two lines, and
  the discordant counts (`b`,`c`) that those p-values and `sign_test_p`/`chi2_mcnemar` would
  need were never archived — WAVE.md's named non-expressible class.
- **3.84** — `grep gpu_hours` over the run tree: 0 hits in any data file; in the source project
  the string occurs only inside the manuscript's own JSON-Schema listing
  (`/data3/.../F2_Theory/main.tex:79,95,102`, example value `0.41`). The only time-shaped
  archived quantities are `real64.json.elapsed = 450.9999`, `real128_combined.json.elapsed =
  1023`, `real192.json.elapsed = 1474` and `real_pilot_qwen2/analysis.json.wall_clock_s =
  1579.4` (sum 2948 s = **0.819 h**). None of the four printed rows (1.47 / 1.10 / 0.85 / 0.42 h)
  equals seconds÷3600; F-A's 1.47 is `real192.json`'s 1474 s ÷ 1000, i.e. kilo-seconds read as
  hours, and no other row follows that rule either. So the column has no carrier and `3.84` is
  only the sum of the table's own cells — `main.tex:184` already states this ("no file in
  `source/` records any GPU-hour value, so the column is the author's accounting"). I did not
  copy the table into a CSV to make `sum` pass: that would be laundering the claim, not
  carrying it.
- **4.84** — occurrences: `source/main.tex:179` (the pre-rewrite draft that printed it),
  `paper/REVIEW_CARD.md:17`, `source/claims.yaml` C06, `paper/REVISION_LOG.md`, and the
  replacement string in `figures/apply_revision.py:211`. Its editorial history is fully
  carried; its *value* is not, and `main.tex:239` is the sentence saying so. Left unroutable
  by design.

## Staged artifacts (2 files, 27,174 B; cap 40 files / 20 MiB)

Neither carries a flagged number; both are staged so the defects below are checkable **inside**
the run root instead of by a path only I can read.

- `paper/evidence/k345/episodes.jsonl` (21,342 B, 180 records) — md5-identical to the source
  project's copy; its byte size is exactly the figure `main.tex:71` says was "quoted from the
  run record rather than from a shipped file". Holds 30 records per $(K,\gamma)$ over 6 groups.
- `paper/evidence/k345/per_seed.jsonl` (5,832 B, 60 records = 6 conditions × 10 seeds,
  `seed` 20260821…20260830) — the per-seed `product` archive.

**Author decision needed:** staging these two files makes `main.tex:71` and `main.tex:244`
("per-seed JSONL … is **not** in the submitted bundle") stale for the bundle as it now stands on
disk. Either keep them out of the shipped bundle or drop those two sentences; I changed no
manuscript text.

## Instrument limits hit here (stated, not fudged)

- No `.md` carrier is executable, so any number whose only home is `protocol.md` /
  `tightness_proof.md` is unreachable regardless of whether the file contains it.
- The op vocabulary has no "fraction of items satisfying X", and `votes`/`holds` leaves are
  nested arrays under a per-condition object, so no rate over `episodes.jsonl` or `real64.json`
  can be expressed in one row. (`figures/REAL_AUDIT_FACTS.json` already stores 63/64 as
  scalars for that reason — the pattern the other four flagged values lack.)

## Checked and sound (not defects)

- `tab:f2a` `bound` column: 0.0312, 0.0312, 0.0228, 0.0228, 0.0181, 0.0181 — one direction
  across every row (successive steps 0, −0.0084, 0, −0.0047, 0); the negative steps **are** the
  $C_{\min}$-decreasing-in-$K$ claim of Theorem 1, and `main.tex:224`'s $K\cdot\text{bound}$
  ≈ 0.090–0.094 reproduces from them (0.0936 / 0.0912 / 0.0905), with both extrapolations
  (0.0150, 0.0138) continuing the decrease. Sound.
- `tab:scale` "Product vs bound": product-first in every row that holds a pair (F-A/F-B/F-C),
  no negative entries, no mixed order.
- The two columns literally headed Paired $\Delta$ (`main.tex:41`, `main.tex:253`) contain only
  words ("Unpaired", "3 seeds", "no $d_z$", "No paired CI", "Not joint", "no"/"yes") — this
  manuscript prints no signed per-row difference column at all.
- All 6 printed products match `analysis_2700.json`/`bootstrap_2700.json` `point` digit-for-digit
  at 2 dp; all 6 printed CIs match that file's `ci_95` at 2 dp; the $\gamma{=}2.0$ rows are
  dropped and footnoted rather than averaged in.
- `tab:scale` cells 4800+4800+4500+3900 = 18,000 ✓; GPU rows 1.47+1.10+0.85+0.42 = 3.84 ✓ (the
  4.84 defect recorded in `source/claims.yaml` C06 is fixed in this draft);
  real-call total 64+128+192 = 384 ✓ = "384 in-file"; 63/64 holds ✓ =
  `figures/REAL_AUDIT_FACTS.json`.
