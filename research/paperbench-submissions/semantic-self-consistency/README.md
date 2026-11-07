# Semantic Self-Consistency — Reproduction Submission

Meaning: reproducing "Semantic Self-Consistency: 语义自一致性" arXiv paper for the
PaperBench task `semantic-self-consistency`.

## Structure
```
submission/
├── src/
│   ├── __init__.py
│   ├── datasets.py     # three datasets, k-shot prompts, loader functions
│   ├── utils.py        # answer parsing, modal, embedding helper
│   ├── embeddings.py   # SciBERT (AQuA/SVAMP) / RoBERTa-base (StrategyQA)
│   ├── methods.py      # CPW, SCW, KNN, IsolationForest, OneClassSVM
│   └── core.py         # full pipeline + MockLM + OpenAILLM
├── tests/
│   └── test_methods.py
├── data/               # downloaded datasets (needs network; fetch_data fills them)
├── results/            # output json
└── run_experiment.py   # CLI entrypoint
```

## Run
```bash
pip install -r requirements.txt
python src/datasets.py fetch_data      # downloads from HuggingFace
python run_experiment.py --lm mock --dataset svamp --limit 2
```

## Methods implemented
1. top-prob sampling (greedy, temperature=0)
2. self-consistency (k=10 samples temp=0.8, modal answer)
3. CPW (centroid proximity weighting)
4. SCW (semantic consensus weighting / cosine)
5. KNN (n=neighbors=5, ball_tree, minkowski metric, top 10% outlier drop)
6. IsolationForest (n_estimators=200, contamination=auto, max_samples=auto)
7. OneClassSVM (kernel=linear, nu=0.01)

## Prompt k-shot
- AQuA-RAT: 4-shot (Table 21, Wei et al., 2022)
- StrategyQA: 6-shot (Table 25, Wei et al., 2022)
- SVAMP: 8-shot (Table 20, Wei et al., 2022)

## Notes
- The MockLM returns deterministic text for smoke-tests. For a real run, supply
  `OPENAI_API_KEY` and use `--lm openai --model gpt-4o-mini` etc.
- We also add the two "any version" models: gpt-3.5-turbo and gpt-4o-mini (configurable).
- All required hyperparameters follow the paper’s Table 2/3 descriptions.

## Real data files

`data/` now includes the three public files verified on 2026-11-07:

- `aqua_test.jsonl` 254 rows, SHA-256 `de41581881ef95...`
- `svamp.json` 1000 rows, SHA-256 `5be77703a6d891...`
- `strategyqa_test.json` 687 rows, SHA-256 `6da41445f044a7...`

`fetch_data.py` downloads from the recorded public URLs when files are absent
and always checks byte length and SHA-256. `src/datasets.py` exposes
`dataset_manifest()` with URLs, sizes, hashes and license notes.
These are public source files, not author-packaged data; byte-level equivalence
to the paper's preprocessing is not claimed.
