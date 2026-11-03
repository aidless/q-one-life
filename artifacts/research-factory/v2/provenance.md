# research-factory-triage v2 provenance

- Generated at: `2026-10-28T12:13:56.237439Z`
- Generator: `src/qone_life/research_factory.py`
- Portfolio: `<WORKSPACE_ROOT>/F:\deepseek/q-one-life/artifacts/research-paper-portfolio/v1/paper-portfolio.json`
- Pilot configuration: `<WORKSPACE_ROOT>/F:\deepseek/q-one-life/research/factory-pilots.json`
- Triage JSON SHA-256: `0465e99261d49dc1a8b98e7d8dac37b8197b83a4c05867afbb30fd8117bbc236`
- Triage Markdown SHA-256: `aafc1310e4086a8141951c41de88d93a792e58481135bd3faadc4e0252eba014`
- Triage CSV SHA-256: `013d7d6f4e6bd6fac171e263a310401ded980fd5bd524f74a35f5aa297bacf58`

## Reproduction

```bash
python scripts/research_factory.py --portfolio '<WORKSPACE_ROOT>/F:\deepseek/q-one-life/artifacts/research-paper-portfolio/v1/paper-portfolio.json' --pilots '<WORKSPACE_ROOT>/F:\deepseek/q-one-life/research/factory-pilots.json' --artifact-dir '<WORKSPACE_ROOT>/F:\deepseek/q-one-life/artifacts/research-factory/v2'
```

The queue is deterministic given the input portfolio and pilot configuration.
It does not modify manuscripts, run experiments, call models, or publish.
