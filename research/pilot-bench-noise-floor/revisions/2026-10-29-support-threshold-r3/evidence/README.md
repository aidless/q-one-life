# R3 evidence overlays

These two files are candidate-local overlays. They do not modify the native
paper tree, its ledger, its verdict registry or its allowlist.

## `paper-ledger-overlay.json`

The file starts from the native `evidence/paper-ledger.json`, records that base
file's SHA-256, and appends six readings introduced by the frozen A3 and A4
experiments. Each appended entry binds a JSON field in one of these receipts:

- `../../experiments/kfold-common-support-a3/results/reproduction.json`
- `../../experiments/threshold-interface-a4/results/reproduction.json`

The appended values are:

- `0.471116`: the A3 mixed-support coherence margin.
- `2.872063`, `0.616016`, `1.851852`: A3 k-fold margins on the joint support
  for coherence, relevance and preference.
- `13.6364`, `21.124`: the A4 interval-crossing fixture's point margin and upper
  interval endpoint.

## `verdict-claims-overlay.json`

The file starts from the native `evidence/verdict-claims.json`, records that
base file's SHA-256, and updates only the windows whose prose R3 deliberately
changes. The new windows still bind the same native carriers. The former
mixed-support EC63 span now requires an empty verdict-token set because R3
removes those current verdict readings from the k-fold paragraph.

## Reproduction

```bash
python3 run_candidate_gates.py \
  --paper-root '/home/liuzewen/F:\deepseek/papers/bench_noise_floor'
```

The command writes the reverse-coverage, anchor-census, verdict-word and
combined summary receipts under `reports/`. Passing these gates proves binding
only; it does not close C02/C03 or authorize an upload.
