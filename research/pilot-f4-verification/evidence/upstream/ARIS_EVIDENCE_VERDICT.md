verdict=FAIL
Dispatch: b1w2-tmlr-f4-verification-20260926T181543Z

Receipt measurement (`python3 tools/carrier_receipts.py --run runs/tmlr-f4-verification`, from the repository root):

    tmlr-f4-verification: PASS=0 FAIL=0 NOT_VERIFIABLE=0 (total 0)

0 of the 20 screen-flagged numbers now carry a PASS receipt — fewer than half, and the gap is not closable
by staging. 18 staged/verified bytes moved: 2 files, 12,256 bytes, into `paper/evidence/` (live tree is
`paper/`). `paper/evidence/CARRIER_RECEIPTS.json` is an empty array: no row was written for a number I could
not honestly claim is carried. Per-number table, search log and the two structural blockers are in
`EVIDENCE_PLAN.md`.

## Findings

- `paper/main.tex:150` — χ²_cc `10.02` does not follow from the row's own `b/c = 38/14`, n_d 52 (recompute 10.17);
  exact McNemar p recomputes to 1.20×10⁻³ against the printed 1.53×10⁻³, which `paper/main.tex:168` repeats as `0.00153`.
- `paper/main.tex:151` — χ²_cc `9.19` vs 11.02 from its stated `36/12`, n_d 48; exact p 7.17×10⁻⁴ vs printed `5.02×10⁻³`
  (also printed at `paper/main.tex:168` as `0.00502`).
- `paper/main.tex:154` — χ²_cc `16.86` vs 17.65 from `41/10`; exact p 1.47×10⁻⁵ vs printed `3.02×10⁻⁶`.
- `paper/main.tex:155` — χ²_cc `6.70` vs 11.03 from `31/9`; exact p 6.80×10⁻⁴ vs printed `9.40×10⁻³`.
- `paper/main.tex:152` — "Seed-pooled 42/43/44" prints `b/c 44/11`, `n_d 55`; the only primary record for those seeds,
  `paper/evidence/per_seed_b_c.jsonl:1-3`, pools to `b=44, c=12, n_d=56` → χ²_cc 17.16 and exact p 2.09×10⁻⁵, not `18.62`/`8.69×10⁻⁶`.
- `paper/main.tex:153` — "single 42" prints `44/11`, n_d 55; primary seed 42 is `14/5`, n_d 19 (≈3× overstated), and this row
  duplicates the three-seed pool of `paper/main.tex:152` digit-for-digit (b/c, n_d, RD, CI, χ², p), which cannot both be true.
- `paper/main.tex:150` — the RD column mixes denominators inside one row: `+0.113` is the arm-rate difference
  (0.810−0.697), while `b/c 38/14` at the caption's n = 300 (`paper/main.tex:143`) gives (b−c)/300 = 0.080; same at `paper/main.tex:151` (+0.100 vs 0.080).
- `paper/main.tex:156` and `paper/main.tex:157` — both Newcombe CIs are the identical interval `[-0.041,0.065]` and each
  excludes its own point estimate (+0.167 and −0.090), so the interval is copied rather than computed.
- `paper/main.tex:143` — the Table 4 caption cites `evidence/per_seed_b_c.jsonl`, and that path resolved nowhere in the run
  before this wave (absent from `paper/`, `source/`, and from `paper/supplementary_tmlr-f4-verification.zip`, which ships only 4 members);
  staged now from the read-only source project, sha256 `ae825d152bb49c0b…`, byte-identical.
- `paper/main.tex:25` — "per-seed JSONL archived": no per-item outcome record exists for the `hist-*`/`prod-*` arms behind
  `0.810`/`0.797`/`0.697` (`paper/main.tex:113`, `paper/main.tex:150-151`); `figures/REPRO_CLAIMS.json:5` records `per_seed_jsonl.files_found: []`.
- `paper/main.tex:113` — calls `0.810`/`0.797`, `8.69×10⁻⁶` and `18.62` "protocol-anchored (protocol.md Table~1, §2)";
  `paper/evidence/protocol.md:1-3` is three lines, has no table and none of those values.
- `paper/main.tex:136` — total GPU-hours `4.00` sums four per-family hours (`paper/main.tex:131-134`) that appear in no data
  file; the only anchor is the prose "runtime 4h" at `paper/evidence/protocol.md:3`, which is a single total with no per-family split.
- `paper/main.tex:168` — Holm `p = 2.76×10⁻⁸` (skill capital) and `5.45×10⁻⁶` (claim graph) have no ablation observations anywhere.
- `paper/main.tex:202` — Brier `0.1139` and ECE `0.1832` have no per-observation `(predicted, label)` records; `paper/main.tex:177` concedes this,
  yet the values are still reported as measurements.
- `paper/main.tex:161` — Wilcoxon `p = 8.60×10⁻⁶` and the `mean(d) == 0.110` assert are attributed to a "single script";
  the archive ships 0 scripts (`paper/sections/evidence_inventory.tex:7`).
- `paper/main.tex:116` — `0.686` "mean majority bound" averages per-study bounds that are archived nowhere; already `NO_CARRIER`
  at `paper/sections/evidence_inventory.tex:36` and `figures/EVIDENCE_RECORD.md:91`.
- `paper/main.tex:179` — "evidence_manifest.json 120 fingerprinted SHA256": `paper/evidence_manifest.json:4` declares **32** entries
  (`figures/MANIFEST_AUDIT.json:5` — match 19 / mismatch 7 / absent 5 / no-hash-field 1) and **no** entry is a `.jsonl`/`.csv`, i.e. the
  integrity envelope never covered an experiment record.

Two limits that no staging can work around, recorded in `EVIDENCE_PLAN.md`: the ten McNemar statistics are functions of
*two* fields (χ²_cc and the exact binomial tail), which the receipt schema (locator | single-array `op`) cannot express; and the
tool rejects the one primary record that holds them — executing a probe row returned `NOT_VERIFIABLE … artifact is not JSON:
paper/evidence/per_seed_b_c.jsonl`. Instrument liveness was positively controlled, not assumed: a genuinely recomputable probe row
(`op: mean` over `grid_results[*].P_mean` in `paper/results/analysis.json`) returned **PASS**, and a row naming a nonexistent
artifact returned `NOT_VERIFIABLE … artifact not on disk`; both probes were transient and the ledger was restored to `[]` before
the final tally above.

Checked: `paper/evidence/cells.jsonl` (staged, sha256 `254d9c6c7ca7e749`) re-derives all of `paper/results/analysis.json` —
270 records = `n_cells`, 10 seeds = `n_seeds`, mean 0.249278→0.2493, population SD 0.028931→0.0289, normal-approx interval
[0.2458,0.2527] = `P_CI95` — but none of those four values is on the screen's flagged list, so it earns no receipt row;
`paper/evidence/baselines/baselines.json`, `paper/evidence/baselines/real40.json`, `paper/results/analysis.json` and
`paper/evidence/protocol.md` verified byte-identical to the source project (already shipped, not re-copied); exhaustive
numeric-leaf and every-executable-`op` search over 890 scalar leaves and 11 numeric arrays across 107 JSON/JSONL files in
`runs/tmlr-f4-verification/` and `/data3/Research/MERGED_FLAGSHIPS/F4_Verification` returned zero candidate matches for 19 of
20 flagged values, and only quantity-invalid digit collisions (`c = 4`, `cell = 4`) for `4.00`, which were refused rather than
receipted; the supplementary zip was opened rather than assumed empty; source project left read-only.
