# Lca On The Line — algorithm slice

This submission is a Q-One minimal reference implementation for PaperBench task
`lca-on-the-line`. It records the rubric categories, exposes a deterministic `run(data)`
interface, and has executable smoke tests.

## What now actually runs

- `src/lca.py` implements the pure-algorithm leaves: LCA, node depth,
  information content `I(y) = -log2 p(y)`, information/depth LCA distances,
  `n x n` distance matrices, and Algorithm 1 alignment loss with CE / BCE
  conditional soft loss, `lambda_weight`, reverse LCA matrix, softmax and one-hot.
- `tests/test_lca.py` has 6 tests; full suite is 9 passed.
- Receipt: `research/validation-20261106/lca-algorithm-slice/receipt.json`.
  Toy taxonomy only: 4 leaves, `I(animal)=1.0`, depth dog-car distance 4,
  CE loss 0.9628, BCE loss 1.4934.

## What is still not reproduced

ImageNet / ImageNet-v2 / Sketch / Rendition / Adversarial / ObjectNet, all 75
vision and vision-language models, WordNet or latent K-means hierarchies,
linear-probe training, R-squared / Pearson / MAE tables, and any real judge
score. No claim of a PaperBench capability score is made.

Rubric leaves: 819. Categories: Code Development, Code Execution, Result Analysis.
Recurring rubric terms: Absolute, Algorithm, Aline-D, Aline-S, Appendix, CLIP_RN50, CLIP_RN50x4, ConvNext.
