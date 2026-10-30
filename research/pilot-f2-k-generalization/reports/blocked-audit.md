# F2 blocked evidence audit

Status marker: `agent-proposed, not human publication approval`

## Reproduces

- 17 unique labels; 32/32 citation keys.
- Two references (`alg:run`, `lst:runschema`) remain unresolved; the source does not pass the structure gate.
- Six condition summaries in `analysis_2700.json`.
- Nine native claims.

## Does not reproduce

- 2,700 archived cells: only five rows over three conditions are stored.
- Six-condition product table: two bootstrap points differ from their per-seed means,
  and the staged per-seed JSONL differs from the analysis on four conditions.
- 270 episodes per condition: the only episode file has 30 records per condition and
  no gamma=2.0 records.
- 466 real-LLM calls: archived call counts sum to 384.
- 144/144 and 90/90: the files name 128 and 64 calls.
- d_z=0.42, h_min=0.08 and causal effect 0.11: no field-level carrier.

## Consequence

The theory sketch may be retained as a proposal. The empirical section cannot be
packaged or uploaded. A rerun with complete per-episode and per-seed archives is
required before another review.
