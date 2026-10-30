# Paper 6 evidence audit

- Scenarios: 4
- Methods: 7
- Seeds: 5
- Rounds per cell: 1000
- Local pilot seeds: 3
- Local methods: 7
- Manifest missing entries: 11

## Winners

| Scenario | Best | Best value | Majority | Majority gap |
|---|---|---:|---:|---:|
| S1: high-honest, weak-attack | trust_median | 0.8886 | 0.8886 | +0.0000 |
| S2: med-honest, weak-attack | trust_median | 0.5528 | 0.5528 | +0.0000 |
| S3: med-honest, strong-attack | trust_median | 0.4592 | 0.4592 | +0.0000 |
| S4: high-honest, strong-attack | trust_mean | 0.8506 | 0.8430 | -0.0076 |

## Checks

- `scenario_count_4`: True
- `method_count_7`: True
- `seed_count_5`: True
- `rounds_1000`: True
- `per_seed_recomputes_aggregate`: True
- `local_pilot_recomputes`: True
- `citations_resolve`: True
- `template_contamination_removed`: True
- `duplicate_reproducibility_removed`: True
- `majority_best_or_tied_s1_s3`: True
- `majority_best_all_scenarios`: False
- `heldout_trace_present`: False
- `hyperparameter_sweeps_present`: False
- `manifest_complete`: False

## Carrier receipts
- Passed: 1 / 1

The frozen per-seed aggregate recomputes. The local pilot also recomputes, but it is only descriptive. No held-out real-trace benchmark or per-cell hyperparameter sweep is present.
