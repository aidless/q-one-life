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
- `research_factory.optimize_portfolio`: ranks families by evidence ROI
  (`publishability / close_cost`). It never produces a quality score.
- `packages/qone-evidence/`: standalone, dependency-free claim ledger
  (`register_claim` / `bind_evidence` / `verify_ledger` / `render_report`).
- `scripts/build_research_index.py`: regenerates `research/INDEX.md`.

```bash
qone-life research-produce --question question.md --venue arxiv --slug demo
qone-life research-adversarial --ledger CLAIM_LEDGER.md --rounds 3 \
  --model group/auto-gpt-6 --output reports/adversarial
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
