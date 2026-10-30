# Q-One research overlay: F2 K-Generalization

Status marker: `agent-proposed, not human publication approval`

- Family: `qf-merged-flagship-f2-k-generalization-sele-112d818110`
- Project: `qp-tmlr-f2-theory-c2a925d103e9`
- Canonical SHA-256:
  `cdf8485e91fe4d1861fc473d4e8f6df3b14431ac984691f529e8a2fb4c072916`
- Disposition: `blocked`
- Package: none
- Uploaded: no

## What is auditable

- 17 unique labels and 32/32 citation keys;
  two labels (`alg:run`, `lst:runschema`) remain unresolved, so the structure gate fails.
- Six condition summaries in `analysis_2700.json`.
- Nine claims in the native ledger.
- A frozen theoretical proof sketch.

## Why the family is blocked

- `joint_2700.json` declares 2,700 records but stores five rows covering only three
  K/gamma conditions; one condition is duplicated with another condition's values.
- `bootstrap_2700.json` point values disagree with the means of their stored
  per-seed arrays on two conditions.
- `per_seed.jsonl` disagrees with `analysis_2700.json` on four of six conditions.
- `episodes.jsonl` has 180 records, not 2,700, and only gamma 0.5 and 1.0.
- The real-LLM subset uses 384 archived calls but is described as 466 frozen calls.
  The 64-call file has one failure, the 128-call file is incomplete, and the
  192-call file has only a summary string.
- The p16 selective effect, p18 drift bound and p21 causal effect have no field-level
  carrier.
- The frozen proof's product range contradicts the abstract.

No package was fabricated from a declared but unarchived sample.
