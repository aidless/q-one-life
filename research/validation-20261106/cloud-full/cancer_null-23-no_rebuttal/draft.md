# cancer_null

## Question
Scaling/regularization under a fixed three-candidate budget.

## Methods
Variant no_rebuttal; seed 23; selected on validation only.

## Recorded results
```json
{
  "validation": 0.5091713069112349,
  "test": 0.5099206349206349,
  "baseline_validation": 0.5091713069112349,
  "baseline_test": 0.4910714285714286,
  "test_delta": 0.018849206349206282,
  "replay_test": 0.5099206349206349,
  "metric_name": "balanced_accuracy"
}
```

## Agent interpretation (validation only)
The validation performance for the logistic model without scaling and with a regularization strength of 10.0 matches the baseline exactly (0.5091713069112349), indicating it is effectively the same as the reference model. The logistic model with scaling and very weak regularization (strength=0.01) performed worse (0.5). The random forest model with scaling and default strength performed substantially below baseline (0.4718).

**Interpretation:**  
The logistic model configuration appears robust; scaling the features does not improve performance and may degrade it with insufficient regularization. The random forest underperforms in this validation split, suggesting it may be overfitting or is poorly suited to the dataset's structure compared to the linear approach.

**Limitations:**  
These results are from a single validation split; performance variance across different data partitions is unknown. Without test-set results, the reported metrics reflect model selection on this validation set and may not generalize. The analysis cannot establish statistical significance or claim one candidate is definitively better than another. The chosen baseline is itself a candidate model, so the comparison is circular for model selection purposes.

## Limitations
Public small dataset; exploratory pilot; no novelty or statistical superiority claim. A numerical gain on shuffled labels is not discovery. No arbitrary code synthesis was tested.
