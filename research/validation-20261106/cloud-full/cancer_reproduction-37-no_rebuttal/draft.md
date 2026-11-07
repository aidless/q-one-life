# cancer_reproduction

## Question
Scaling/regularization under a fixed three-candidate budget.

## Methods
Variant no_rebuttal; seed 37; selected on validation only.

## Recorded results
```json
{
  "validation": 0.9510317720275139,
  "test": 0.9742063492063492,
  "baseline_validation": 0.9626596790042581,
  "baseline_test": 0.9265873015873016,
  "test_delta": 0.04761904761904756,
  "replay_test": 0.9742063492063492,
  "metric_name": "balanced_accuracy"
}
```

## Agent interpretation (validation only)
Validation accuracy for logistic regression with strength 0.001 is notably lower (0.837) than the baseline (0.963), suggesting under-regularization or insufficient model capacity to fit this split.

The best-performing candidate is logistic regression with strength 1.0 (validation accuracy 0.951), closely approaching the baseline. This model benefits from both scaling and moderate regularization. The random forest candidate (strength 10.0, no scaling) achieves competitive performance (0.939) without feature scaling, indicating inherent robustness to input scales.

Limitations: These results are from a single validation split; performance may vary across different data partitions. Without test-set results, generalization to unseen data is unconfirmed. Model selection based solely on this validation set risks overfitting to its particular characteristics. The baseline model (accuracy 0.963) remains superior, and none of the evaluated candidates surpassed it on this split. All conclusions are provisional pending evaluation on a held-out test set.

## Limitations
Public small dataset; exploratory pilot; no novelty or statistical superiority claim. A numerical gain on shuffled labels is not discovery. No arbitrary code synthesis was tested.
