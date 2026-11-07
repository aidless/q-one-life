# Q-One Research

This directory holds research-domain overlays and portfolio configuration. The
inventory layer is read-only: it records source locations, hashes, duplicates,
claims, evidence state, and blockers without rewriting manuscripts. Research
Factory overlays are external directories; they do not modify source papers.

## Q1 deliverables

- `../docs/RESEARCH_QUANTIFICATION.zh-CN.md`: quantification model and gates.
- `../schemas/research-project.schema.json`: one paper project and its evidence.
- `../schemas/paper-portfolio.schema.json`: the deduplicated paper inventory.
- `portfolio-sources.json`: roots and exclusions used for the first scan.
- `arc-paper-track/`: an evidence overlay for the published Kaggle writeup and
  prospective arXiv preprint.

## Current portfolio snapshot

The first scan is stored at:

- `../artifacts/research-paper-portfolio/v1/paper-portfolio.json`
- `../artifacts/research-paper-portfolio/v1/paper-portfolio.md`
- `../artifacts/research-paper-portfolio/v1/paper-triage.csv`
- `../artifacts/research-paper-portfolio/v1/artifact.json`
- `../artifacts/research-paper-portfolio/v1/provenance.md`

It separates:

- raw marker roots;
- exact byte duplicates;
- normalized-title version families;
- Q-One `project.json` metadata overlays matched by normalized title;
- supporting manifests and claim ledgers that are not standalone papers.

Status is `unknown` unless a project manifest explicitly records it. Unknown is
not converted to a score.

## Research Factory v2

The second layer is implemented in `../src/qone_life/research_factory.py` and
`../docs/RESEARCH_FACTORY_90_DAY_PLAN.zh-CN.md`.

It provides:

- `research-triage`: a transparent production queue, separately from human
  disposition and without a paper-quality score;
- `research-scaffold`: a non-destructive external overlay for one paper family;
- `research-plan`: evidence-gated next actions for one project;
- `research-package-check`: a mechanical LaTeX source-tree audit;
- `research-native-ledger`: source/field/value audit for native numeric ledgers;
- `scripts/cleanroom_compile.py`: isolated two-run LaTeX compilation;
- `scripts/build_arxiv_archive.py`: deterministic internal candidate archive;
- `scripts/research_review_packets.py`: 131-family review packets and Top-20;
- `scripts/research_factory_verify.py`: factory-wide verification refresh.

### Research production pipeline (v3)

Five-axis upgrade that turns the factory from an audit tool into a production
pipeline. Local machines orchestrate only; every experiment runs on the remote
AMD node (`root@36.150.116.206:34677`).

- `src/qone_life/cloud_executor.py`: SSH job submission, status polling and
  hash-verified output fetch. Hard limits are 2 concurrent jobs, 4 hours and
  50GB per job.
- `src/qone_life/research_production.py`: seven gated stages (question →
  hypothesis → experiment plan → cloud execution → results → claim ledger →
  draft). A stage refuses to run unless every earlier stage passed.
- `src/qone_life/adversarial_review.py`: multi-round counterexample, boundary
  and alternative-explanation attacks routed through the Magpie gateway.
  Unreachable models mark the round `inconclusive` rather than passing it.
- `src/qone_life/rebuttal_loop.py`: classifies adversarial objections into
  executable vs out-of-loop, drafts a rebuttal experiment per executable
  objection, and never claims novelty objections are resolvable.
- `src/qone_life/research_factory/autopilot.py`: generates candidate
  hypotheses from a question and screens them with an injected proxy scorer.
  Missing scores are `inconclusive`, not zero; a majority-inconclusive batch
  is `blocked`.
- `src/qone_life/research_factory/review_rubric.py`: mechanical checks plus a
  weighted model rubric. A total is computed only when every mechanical check
  passes and all three dimensions are scored.
- `src/qone_life/research_factory/writer.py`: renders a LaTeX draft where every
  number must be a `{{num:key}}` placeholder bound to the results receipt;
  bare numbers and unresolved keys fail closed.
- `src/qone_life/research_factory/meta_review.py`: aggregates rubric,
  adversarial review and rebuttal into `stop` / `continue` / `rollback`;
  `stop` means human review, not acceptance.
- `src/qone_life/research_factory/autopilot.py:run_batch`: runs generation and
  screening over a list of questions; a failing item is recorded without
  aborting the rest of the batch.
- `src/qone_life/research_factory/rubric_calibration.py`: negative controls and
  human-score alignment. Without human labels the status is `partial`, never
  `calibrated`.
- `src/qone_life/research_factory/research_integrity.py`: deterministic subset
  of the RIDAR RIVT taxonomy. Six types are checked; the other eight are
  `not_assessed`, and release stays withheld until every check passes.
- `src/qone_life/research_factory/rubric_types.py`: type-level structural
  rubrics for empirical ML, benchmark, systems, theory, audit and survey
  papers; it checks completeness, not argument quality.
- `src/qone_life/research_factory/environment_manifest.py`: locks a paper's
  baseline into an executable environment (datasets, metrics, tolerance,
  command, resource limits) and validates it.
- `src/qone_life/research_factory/direction_diversity.py`: greedy allocation
  with a direction exploration bonus, following Coral Discovery's idea of
  dividing cognitive labour.
- `src/qone_life/research_factory/outcome_predictor.py`: ranks candidate plans
  by predicted outcome; low-confidence and unpredicted plans enter `must_run`.
- `research_factory.optimize_portfolio`: ranks families by evidence ROI
  (`publishability / close_cost`). It never produces a quality score.
- `packages/qone-evidence/`: standalone, dependency-free claim ledger
  (`register_claim` / `bind_evidence` / `verify_ledger` / `render_report`).
- `scripts/build_research_index.py`: regenerates `research/INDEX.md`.

```bash
qone-life research-produce --question question.md --venue arxiv --slug demo
qone-life research-adversarial --ledger CLAIM_LEDGER.md --rounds 3 \
  --model group/auto-gpt-6 --output reports/adversarial
qone-life research-rebuttal --attack-output reports/adversarial \
  --output reports/REBUTTAL_PLAN.md
qone-life research-autopilot --question question.md \
  --output reports/hypotheses.json --n 5
qone-life research-screen --candidates reports/hypotheses.json \
  --output reports/screening.json --top-k 2
qone-life research-review --manuscript draft/main.tex \
  --ledger CLAIM_LEDGER.md --output reports/review.json
qone-life research-write --title "T" --question question.md \
  --hypothesis hypothesis.json --claims CLAIM_LEDGER.md \
  --results results.json --output draft/main.tex
qone-life research-decide --rubric reports/review.json \
  --adversarial reports/adversarial/summary.json \
  --rebuttal reports/rebuttal/plan.json --output reports/decision.json
qone-life research-batch --items batch.json --output-dir reports/batch
qone-life research-calibrate --output reports/calibration.json \
  --human-records human_scores.json
qone-life research-integrity --manuscript draft/main.tex \
  --ledger CLAIM_LEDGER.md --results results.json \
  --output reports/integrity.json
qone-life research-type-rubric --manuscript draft/main.tex \
  --type audit --output reports/type-rubric.json
qone-life research-environment-check --manifest env.json \
  --root . --output reports/environment.json
qone-life research-directions --items families.json \
  --capacity 5 --output reports/directions.json
qone-life research-screen-plans --plans plans.json \
  --predictions predictions.json --output reports/screen.json
qone-life research-optimize --portfolio <portfolio.json> --pilots \
  research/factory-pilots.json --capacity 5 --output allocation.json
qone-life measure-decide --subject pick-next-paper --option a --option b \
  --chosen a --rationale "closest to publishable" --evidence ledger \
  --expected-outcome "3 days"
```

Example local commands:

```bash
PYTHONPATH=src python3 -c 'from qone_life.cli import main; raise SystemExit(main([
  "research-triage",
  "--portfolio", "artifacts/research-paper-portfolio/v1/paper-portfolio.json",
  "--pilots", "research/factory-pilots.json",
  "--output", "artifacts/research-factory/v2/triage.json",
  "--markdown", "artifacts/research-factory/v2/triage.md",
  "--csv", "artifacts/research-factory/v2/triage.csv",
]))'
PYTHONPATH=src python3 -c 'from qone_life.cli import main; raise SystemExit(main([
  "research-validate", "--project", "research/pilot-paper11"
]))'
```

`factory-pilots.json` pins the first five pilots: Paper11 harness selection,
benchmark noise floor, f-acceptance, Gemma tool selection, and ARC. Pinning
changes production order only. It is not a readiness claim.

## Current gates

1. Obtain an independent method/statistics review bound to the current
   f-acceptance source hash.
2. Resolve the Noise Floor producer-baseline issue and source-manifest mismatch
   without silently rewriting either receipt.
3. Recover the exact Gemma publication source, then build a LaTeX arXiv source.
4. Capture ARC's official scoring methodology and exact published source bytes.
5. Keep the 131-family human triage separate from the machine queue; no automatic
   `arxiv-ready` disposition is allowed.

## Validation pilot (2026-11-06)

`validation-20261106/` holds the first bounded end-to-end check of the factory:
54 cloud traces over 6 tasks, 3 seeds and 3 variants, with a shuffled-label
control, a 10-class fault-injection battery and an exploratory PeerRead
external check. Start at `validation-20261106/REPORT.zh-CN.md`; the machine
summary is `validation-20261106/results.json` and `verification.json` reruns the
headline numbers from the receipts.

Result in one line: receipts, replay and test isolation hold, but the
multi-agent role split shows no advantage over single-agent or no-rebuttal
(sign tests p=0.73 and p=0.69), and shuffled-label controls show gains of the
same magnitude.

Data follow-up: all 60 RIDAR RIV-Gold traces are now local and verified
(47,797 records, 3,461 evidence spans, 13/14 categories). None of the six
implemented integrity checks reads traces, so trace-level detection remains
unmeasured. PaperBench is preflighted but blocked on Docker, GPU and paid judge
credentials (`validation-20261106/paperbench-preflight.zh-CN.md`).

Current citable claims and explicit non-claims are collected in
`../docs/AI_RESEARCHER_CURRENT_CLAIMS.zh-CN.md`. Key boundary: the 28-paper
PeerRead set is the fixed-revision ceiling, the multi-agent split shows no
advantage in 10 pairs, and all three fixed-pattern RIDAR TCE rules failed the
frozen precision floor.

Stage closure is recorded in
`../docs/AI_RESEARCHER_CLOSURE_20261106.zh-CN.md`; the machine gate currently
recomputes 42 headline checks and all available non-dependency tests pass.
