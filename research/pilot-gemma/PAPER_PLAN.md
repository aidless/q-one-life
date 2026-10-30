# PAPER_PLAN.md — Gemma Tool Selection

Generated 2026-10-30. This file is the plan the draft already follows, reconstructed from the draft: it is a *reconciliation*, not a promise about work not yet done.

## What this paper argues

From the draft's own abstract, verbatim (source `source/WRITEUP.md`):

> Substring matching can credit the name of one tool when an output contains only a longer identifier, such as `get_stock_v1` instead of `get_stock`. We audit a published archive of 450 tool-selection records and distinguish this string-scoring defect from semantic correctness of an executed call. Twelve recorded positives contain only a longer identifier while the complete recorded output lacks the gold identifier. Twelve further positives cannot be resolved from the truncated record. These counts support a discrepancy between substring and whole-identifier scoring; they do not establish execution accuracy. The archive also contains only 75 distinct record signatures when grouped by registry size, each repeated six times. Because prompts and row-level registries are absent, independence of the underlying trials cannot be established. We therefore withdraw independent-trial significance claims and release a reproducible audit, negative controls, and a record format for stronger future evaluation.

## Section plan, as the draft implements it

1. **Question and scope** — the substring-vs-whole-identifier distinction; what whole-identifier still does not establish (C01, C02).
2. **Evidence and reproducible procedure** — the published evidence kit, the scorer, the replay; controls that reject the injected defects.
3. **Results that the record supports** — the 450-row / 120-positive / 96-whole / 12-discrepancy / 12-unresolved table (C01, C02); the text-measurement caveat (12-24 conditional interval).
4. **Duplication and independence** — 75 distinct registry-record pairs, each signature repeated six times (C03); the withdrawal of independent-trial significance.
5. **Cross-model probe** — the fresh 48-row probe (Qwen 22/24 + 21/24, Llama 10/24 + 7/24) (C04).
6. **Reproducible release** — the audit, negative controls, record format.

## How the numbers in it were checked

`validation_path: bounded_subset_rerun` — 5 printed numbers with no ledger entry; all 5 non-data (model names / hyphen parsing). 4 registered claims (C01-C04) all `verified`.

## Evidence Record

- **live draft**: `source/WRITEUP.md` (local copy; **source identity differs from the published remote source** — see Notes)
- **published remote source**: SHA-256 `aa25d33d83b55c4bff5716f2777f420b182122faf93b26a78694b5ce9c5ea798`
- **Claim Ledger**: `CLAIM_LEDGER.md` (4 claims C01-C04, all `verified`)
- **evidence**: `evidence/toolselect_replay_audit.json`, `evidence/toolselect_recompute.json`, `evidence/toolselect_cross_model_analysis.json`
- **validation_path basis**: `bind_numbers_tool.py --run` (re-executed)

## Notes for the drafting phase

- **Source identity not established**: the local `WRITEUP.md` and the published remote source (SHA-256 `aa25d3...`) differ. Before arXiv package, the published bytes must be recovered or the local source re-verified against the published identity. This is the pilot's declared first-stage blocker (90-day plan pilot 4).
- No new numeric claim without a registered evidence field.
- The `12-24` conditional interval and the significance withdrawal are core honest-scope statements.
