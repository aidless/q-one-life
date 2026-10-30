# External Judge Report — 5% Sample

Total judged: 120 samples.

## Per-cell ΔECE (judge-based)

| condition_id | n_judged | n_valid | ECE_biased | ECE_clean | ΔECE_judged |
|---|---:|---:|---:|---:|---:|
| Q-A-08 | 20 | 20 | 1.000 | 1.000 | 0.000 |
| Q-S-08 | 20 | 20 | 1.000 | 0.996 | 0.004 |
| Q-R-08 | 20 | 20 | 1.000 | 0.994 | 0.006 |
| Q-A-AU | 20 | 20 | 1.000 | 0.994 | 0.006 |
| Q-S-AU | 20 | 20 | 0.996 | 1.000 | -0.004 |
| Q-R-AU | 20 | 20 | 1.000 | 0.996 | 0.004 |

## Interpretation
ΔECE_judged is the calibration degradation under the **external**
judge's verdict, providing a stricter bound than the model's
self-reported confidence. If |ΔECE_judged| < |ΔECE_self|,
the headline ECE numbers in main.tex are conservative; if not,
the judge exposes additional calibration drift that the in-loop
score missed.
