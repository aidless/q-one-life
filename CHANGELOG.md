# Changelog

## Unreleased

- Stated the product as a local decision workbench, not medical or financial advice, and not an executor of consequential acts.
- Split the record-only CLI smoke from the fixture test job. Live model smoke stays a manual local script.
- Documented recommendation hallucination, cache staleness, and budget-versus-free-time in `FAILURE_MODES.md`.
- A failed refresh no longer labels an existing model card as a rule draft.
- Aligned the research manifest version with the package and left `experiments` empty.

## 0.7.1 — 2026-10-26

- Pinned the app to the evidence-gate core release (0.4.1).
- Added end-to-end checks for atomic exclusion of conflicting outcome evidence without changing action definitions, resources, or recommendation authority.
- Displayed the evidence denominators and exclusion reasons in the recommendation evidence panel.

## 0.7.0 — 2026-10-26

- Added local observation and outcome intake. The scope and the statement that this is not a life-benefit result are in `docs/OUTCOME_INTAKE.zh-CN.md`. `artifacts/outcome-intake/v1/results.json` records package version 0.7.0.

## 0.6.0 — 2026-10-25

- Added a calibration shadow that does not change recommendations. `docs/evidence/calibration-installed-acceptance.json` records `q-one-life` 0.6.0 and `used_for_recommendations: false`.

## 0.5.0 — 2026-10-25

- Added life-model import and inspect. `docs/evidence/kernel-installed-acceptance.json` records `q-one-life` 0.5.0 on synthetic data.

## 0.4.0 — 2026-10-24

- Rebuilt the homepage as Decision Studio. Scope and limits are in `docs/DECISION_STUDIO.zh-CN.md`.

## 0.3.0 — 2026-10-24

- Made proactive recommendations the main product flow, starting from goals without a decision/baseline form.
- Added automatic lifecycle scheduling, local Ollama generation, Laya candidate ranking, explicit rule fallback and bounded refresh.
- Added daily time budgets, accept/dismiss feedback, next steps after completion, and stale-proposal/configuration guards.
- Added goal management, automatic homepage updates, private input/output receipts and v1-compatible v2 backups.

## 0.2.0 — 2026-10-24

- Added the complete Chinese personal workspace, local persistence and model integration.
- Added decisions, tasks, directional metrics, corrected observations, source retrieval and reviews.
- Added private backup validation/recovery, redacted exports and model configuration.
- Added install/start entry points, product documentation and acceptance evidence.

## Recorded without a version tag

- Added source-linked Chinese research synthesis and implementation priorities.
- Clarified prototype status and pending real-model acceptance.

## 0.1.0 — 2026-10-23

- Added local observation storage with an append-only hash chain.
- Added user-defined metric specifications and dimension-vector scoring.
- Added review prompts, missingness reporting, and redacted exports.
- Added ontology, scoring, and privacy documentation.
