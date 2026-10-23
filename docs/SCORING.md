# Dimension scoring

For a metric with range `[minimum, maximum]`, each in-range observation is normalized as:

```text
(value - minimum) / (maximum - minimum)
```

Repeated observations are averaged. A domain score is the weighted mean of observed metric scores in that domain. Each domain also reports:

- `observed_metrics` and `expected_metrics`
- `coverage`
- per-metric observation count and target count
- the latest observation timestamp

Observations outside the current metric specification are excluded and listed as a limitation. The original event stays unchanged so the user can revise the specification and recompute the report.

There is deliberately no global score. A scalar can hide tradeoffs, missing data, and value judgments. If a future experiment proposes a composite, it must be a separate, versioned analysis with explicit user consent and sensitivity checks.
