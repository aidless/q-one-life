# cancer_null

## Question
Scaling/regularization under a fixed three-candidate budget.

## Methods
Variant single_agent; seed 37; selected on validation only.

## Recorded results
```json
{
  "validation": 0.5067147068457255,
  "test": 0.5099206349206349,
  "baseline_validation": 0.48804454634785455,
  "baseline_test": 0.4910714285714286,
  "test_delta": 0.018849206349206282,
  "replay_test": 0.5099206349206349,
  "metric_name": "balanced_accuracy"
}
```

## Agent interpretation (validation only)
The candidate models show modest improvements over the baseline (0.488) in validation performance. The forest model with scaling and strength 1.0 achieved the highest validation score (0.507). Both logistic models also exceeded the baseline, with the unscaled, high-strength variant (0.500) slightly outperforming the scaled, low-strength one (0.493).

These results suggest that moving from a simple logistic model to an ensemble method (forest) provided a measurable gain in validation performance, and that regularization strength and feature scaling interact with model family. However, without test-set evaluation, the reported validation scores reflect in-sample selection and are optimistically biased. The observed differences are small; without significance testing, they could stem from random variation.

Limitations: This analysis is constrained to a single validation split. The absence of test results means any performance claims are provisional and subject to overfitting from model selection. The small magnitude of improvements (≤0.02) relative to the baseline warrants caution—the practical significance is unclear. Future work should include cross‑validation, statistical testing, and hold‑out test evaluation to confirm generalizability.

## Limitations
Public small dataset; exploratory pilot; no novelty or statistical superiority claim. A numerical gain on shuffled labels is not discovery. No arbitrary code synthesis was tested.
