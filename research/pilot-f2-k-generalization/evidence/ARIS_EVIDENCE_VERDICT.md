verdict=FAIL
Dispatch: b1w4-tmlr-f2-theory-20260927T034219Z

Instrument: `python3 tools/carrier_receipts.py --run runs/tmlr-f2-theory` ->
`tmlr-f2-theory: PASS=0 FAIL=0 NOT_VERIFIABLE=0 (total 0)`

Placed: 0 of the 7 screen-flagged values (`paper/main.tex` lines 24, 45, 47, 124, 136, 184,
190, 239). Fewer than half, deliberately: `paper/evidence/CARRIER_RECEIPTS.json` is an empty
array because no executable derivation exists for any of the 7, and the honest alternative —
recopying the manuscript's own table into a CSV so `sum` would pass — is laundering a claim,
not carrying it. Per-number dispositions, searches run and reason classes:
`EVIDENCE_PLAN.md`.

## Findings

- `paper/main.tex:124` — the carrier this sentence names does not contain the numbers. It
  asserts that `$H{\ge}0.85$, coverage${\ge}0.90$, $0.810/0.797$, $w_c{=}50$, violations $0$,
  takeover $0.00$` "are declared in \texttt{evidence/protocol.md} Table~1";
  `paper/evidence/protocol.md` is 4 lines / 219 B with no table and none of those 7 tokens
  (grep: 0 hits). The pair survives only as author-to-do prose in
  `paper/100_suggestions.md:55,57`, where the same item is ticked ✅ at
  `paper/100_suggestions_checked.md:67`. Both flagged values therefore have no carrier, and
  the pointer that promises one is false.
- `paper/main.tex:187`, `paper/main.tex:188`, `paper/main.tex:190` (Table `tab:scale`, "Real
  LLM" column) — one column, two counting orders. Row **F-B** asserts `144/144` while its own
  Provenance cell in the same row states `\texttt{real128_combined}: 128 calls`; row **F-C**
  asserts `90/90` while its own cell states `\texttt{real64.json}: 64 calls`. Order 1 = the
  frozen-subset claim (192/144/90/40, summing to 466); order 2 = the archived call counts
  (192/128/64, summing to 384), and the **Total** row adds on order 2 ("384 in-file") while
  the cells above it are written on order 1 — so the column does not sum to its own total. The
  abstract repeats order 1 as "frozen real-LLM subsets $192/144/90/40$" (`paper/main.tex:24`).
- `paper/main.tex:189` — same table, "Product vs bound" column: row F-D puts `$d_z{=}0.42$`
  where rows F-A/F-B/F-C put a product/bound pair, so one column carries two quantities; the
  digit 0.42 also appears in that same row as its GPU-hours, and collides with F-B's product
  (0.42). F-D's `40/40` has no carrier either — the file it names,
  `paper/evidence/p16_provenance.json`, records `total_cells: 300` and no holds field.
- `paper/main.tex:164` — "the file itself carries 5 rows (one per $K,\gamma$ condition)" is
  false: `paper/evidence/k345/joint_2700.json`'s `cells` list has 5 rows covering only **3**
  distinct conditions (K3_g0.5 ×2, K4_g1.0 ×2, K5_g2.0 ×1); 4 of the 6 carried conditions have
  no row at all, and the K5_g2.0 row is a copy of K3_g0.5's `product: 0.4777` /
  `bound: 0.0312` — the (K,γ)↔value scramble `paper/REVIEW_CARD.md:13` item 1 already names.
  `n_cells: 2700` and `holds: 2700` are declared scalars over those 5 rows.
- `paper/main.tex:157`, `:158`, `:159` (Table `tab:f2a`, product column) — for 3 of the 6 rows
  the printed product is not the mean of the ten per-seed values stored in the very file the
  caption names as its interval carrier (`paper/main.tex:143-144`). In
  `paper/evidence/k345/bootstrap_2700.json`, `mean(per_seed)` gives 0.3441 / 0.5363 / 0.4144
  where the table prints 0.35 / 0.53 / 0.42; only K3_g0.5 satisfies point == mean(per_seed)
  exactly (0.4777). `figures/make_f2_artifacts.py:52` reads `point`, so the printed value and
  the plotted per-seed cloud (`paper/main.tex:176-177`) come from different fields of one file
  and disagree at the printed precision on half the rows.
- `paper/evidence/k345/per_seed.jsonl` (staged this wave, 60 records, 6 conditions × 10 seeds)
  disagrees with both of them: its per-condition means are 0.4854 / 0.3544 / 0.5332 / 0.4293 /
  0.5477 / 0.4264, which differ from the printed 0.48 / 0.35 / 0.53 / 0.42 / 0.56 / 0.44 on 4
  of 6 rows at 2 dp. So three archives claim to be "the" per-seed products for the same cells
  and none of the two non-`point` ones reproduces the table. This is invisible today only
  because `paper/main.tex:71` and `paper/main.tex:244` state the per-seed JSONL is not in the
  bundle; staging it makes those two sentences stale, which is an author decision, not mine.
- `paper/main.tex:156` episodes column ("270 eps" on all six rows) is a pilot total printed as
  a per-condition count. `paper/evidence/k345/analysis_2700.json` stamps
  `n_episodes: 270` on each of 6 conditions (6 × 270 × 10 seeds = 16,200, not 2,700), while
  the only per-episode record, `paper/evidence/k345/episodes.jsonl` (180 records; the 21,342 B
  file whose byte count `paper/main.tex:71` quotes), holds exactly 30 episodes per (K,γ) and
  no γ=2.0 episodes at all.
- `paper/main.tex:235` — "(Table~\ref{tab:f2a} with McNemar)" points at content the live table
  does not have: `tab:f2a` (`paper/main.tex:140-162`) has no McNemar column, count or p-value,
  and the literals 18.62, 8.69e-06, 0.257, 0.063/0.157 appear nowhere in `paper/main.tex`. The
  statistic set (b=44, c=11, n_d=55, χ²=18.62) exists only in the pre-rewrite manuscript
  `/data3/Research/MERGED_FLAGSHIPS/F2_Theory/main.tex:139`. Its arithmetic is fine
  (χ²(44,11)=18.618, 44+11=55), but the counts have no carrier here, and
  `paper/REVIEW_CARD.md:19` records the identical (44,11) pair appearing verbatim in a
  different paper — so the reference is both dangling and unowned.
- `paper/CLAIM_LEDGER.md:6,8,9,10` — four rows are stamped `verified` against carriers that
  contain none of their values: C02 "Product 0.14-0.26" -> `ten_seed_cloud_provenance.json`
  (8 keys, no product/0.14/0.26); C04 "dz 0.42 CI [0.18,0.66] p=0.009" ->
  `p16_provenance.json` (no dz/CI/p field); C05 and C06 (0.08 [0.05,0.12]; 0.11 [0.02,0.20]) ->
  `evidence/protocol.md`, which has 4 lines and none of those numbers. The ledger's own
  coverage is also misstated twice in the manuscript — `paper/main.tex:52` "9 claims, 9 PASS"
  vs the file's 8 `verified` + 1 `not_assessed`, and `paper/main.tex:247` "Ledger 86 PASS".
  None of the 7 flagged values appears in the ledger at all.
- `paper/evidence/tightness_proof.md:9` — the file `paper/main.tex:21`, `:24` and `:136` cite
  as the frozen carrier contradicts the abstract it is cited for: it states "9/9 holds for 2700
  cells (product 0.14-0.26 vs bound 0.018-0.031)" where the abstract states "all six carried
  conditions hold" and "product $0.35$--$0.56$". Line 8 of the same file is the *only* carrier
  of the flagged `0.686`, and it is prose: the instrument loads `.json/.jsonl/.csv` only, so
  that number is unreachable by receipt regardless of the file's contents.
- `paper/main.tex:184` and `paper/main.tex:24` — the GPU-hour column is presented as a
  measurement column ("Each family reports GPU-hours … measured wall-clock") three sentences
  before conceding it is not ("no file in `source/` records any GPU-hour value"). Both
  statements are in the same paragraph, and the flagged total `3.84` is the sum of the four
  unbacked cells. Related and checkable: none of 1.47/1.10/0.85/0.42 h equals the archived
  `elapsed` fields read as seconds÷3600 (real192 1474 s = 0.409 h, real128 1023 s = 0.284 h,
  real64 451 s = 0.125 h, all three summed = 0.819 h), and F-A's 1.47 is exactly real192's
  1474 ÷ 1000 — kilo-seconds in an hours column. `4.84` (`paper/main.tex:239`) is correctly
  self-described as a withdrawn value with no carrier; no finding there.

Checked: `tab:f2a`'s bound column is one consistent direction across every row (0.0312,
0.0312, 0.0228, 0.0228, 0.0181, 0.0181; steps 0, −0.0084, 0, −0.0047, 0), and the negative
steps ARE the paper's Theorem-1 claim that C_min decreases in K — not an inconsistency — with
`paper/main.tex:224`'s K·bound ≈ 0.090–0.094 reproducing from them (0.0936/0.0912/0.0905) and
both extrapolations (0.0150, 0.0138) continuing the decrease; `tab:scale`'s "Product vs bound"
column is product-first in every row that holds a pair, with no negative entry and no second
order; the two columns headed Paired $\Delta$ (`paper/main.tex:41`, `paper/main.tex:253`)
contain only words ("Unpaired", "no $d_z$", "No paired CI", "Not joint", "no", "yes"), so this
manuscript prints no signed per-row difference column anywhere and the only difference
quantity in it, $d_z{=}0.42$, has no per-pair archive (`p16_provenance.json` has no `d`
field); all 6 printed products match `analysis_2700.json`/`bootstrap_2700.json` `point` at
2 dp and all 6 printed CIs match that file's `ci_95` at 2 dp; `tab:scale` cells sum to 18,000
(4800+4800+4500+3900) and its GPU rows do sum to 3.84 (1.47+1.10+0.85+0.42), i.e. the 4.84
recorded in `source/claims.yaml` C06 is fixed in this draft; real calls 64+128+192 = 384 =
"384 in-file" and 63/64 holds match `figures/REAL_AUDIT_FACTS.json`; `figures/
make_f2_artifacts.py` reads every printed number from the JSON at run time — no hard-coded
value in the figure or table generator, so that class of finding does not apply here.
