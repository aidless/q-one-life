# Pipeline state

Status marker: `agent-proposed, not human publication approval`

| Stage | State | Evidence |
|---|---|---|
| Source identity | passed | `evidence/source_record.json` |
| Variant reconciliation | passed | `evidence/variant-reconciliation.json`; 6 distinct hashes |
| Carrier transcription | passed | 11/11 receipt rows resolve |
| Simulation gamma recomputation | passed | three means reproduce from 15 seeds |
| Simulation CV recomputation | blocked | nearest gaps 0.0297, 0.0164, 0.0290 |
| Real-API result | blocked | CG and CG+TEE degenerate on 15/15 seeds |
| Parser provenance | passed | silent 0.5 fallback is pinned in sanitized evidence |
| N=15 model identity | blocked | no result JSON records endpoint or model |
| Citation parse | passed | 26/26 keys resolve |
| Independent review | blocked | upstream review remains Reject |
| Clean-room compile | passed | 10 pages, two identical PDF hashes |
| Candidate package | compiled | internal only; not upload-authorized |
| Upload | locked | user metadata, license, and authorization gate |

## Next valid action

Run a parser-fixed N=15 experiment with explicit endpoint/model identity,
parser-success counts, per-seed CV outputs, and a preregistered aggregation
rule. Do not repair the current CV column by inference.
