# Q-One Life

> 中文研究入口：[多学科融合实现路线](docs/SYNTHESIS_IMPLEMENTATION.zh-CN.md)。当前为初版原型，真实模型接入与端到端验收尚未完成。

Q-One Life is the third repository in the Q-One system. It stores personal observations locally, maps them to user-defined dimensions, and produces review prompts. It keeps a vector of dimensions instead of a single “life score”.

The included examples are only templates. A metric range, weight, and target count must be chosen by the user for a specific context; they are not universal measures of health, productivity, or worth.

## Relationship to the other repositories

- [`q-one-core`](https://github.com/aidless/q-one-core) records bounded decisions and outcomes.
- [`q-one-agent`](https://github.com/aidless/q-one-agent) produces human-reviewed recommendations.
- `q-one-life` stores personal observations, reviews, and explicit exports.

An observation can optionally include a `decision_id` so a review can connect a personal measurement to a core decision without copying the whole private context into the agent repository.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .

qone-life --data-dir .life-data init
qone-life --data-dir .life-data add-observation \
  --domain energy --metric sleep_quality \
  --value 7 --minimum 0 --maximum 10 \
  --source self-report
qone-life --data-dir .life-data score --spec-file examples/metric-spec.json
qone-life --data-dir .life-data review --spec-file examples/metric-spec.json
qone-life --data-dir .life-data export
qone-life --data-dir .life-data verify
```

The default export is redacted. Use `export --full` only when the destination is private and you have reviewed the fields.

## Scoring contract

Each metric is normalized to its declared range. Repeated observations are averaged for that metric. Dimensions report a score, observation count, target coverage, and missingness. The report intentionally sets `global_score` to `null`; a person is not reduced to one scalar.

The score is descriptive. It does not diagnose a condition, predict a life outcome, or establish causality. Keep the original observation and the metric definition so a later review can reproduce or revise the calculation.

Read [docs/ONTOLOGY.md](docs/ONTOLOGY.md), [docs/SCORING.md](docs/SCORING.md), and [docs/PRIVACY.md](docs/PRIVACY.md) before adding integrations.

This repository is MIT licensed.
