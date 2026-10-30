# P9 evidence audit

Status marker: `agent-proposed, not human publication approval`

## Source and identity

- Local source SHA-256:
  `e9487a094e1377549572faaa207cdff9f0f99a72d8903518186dac3a953e3d03`
- arXiv identity: `2606.31371v1`
- Title match: yes
- Listed author: Zewen Liu
- arXiv response SHA-256:
  `0282cfb9892c7df04a239e77f5d80c1fa6baa5c78edc066f9b5cf6b49ef22632`

## Scale contradiction

| Quantity | Manuscript | Archived driver |
|---|---:|---:|
| TTRL rounds | 2,400 | 1,200 |
| Executor calls | 2,400 | 2,400 |
| Evaluator calls | 3,600 | 1,800 |

The driver's four training phases per mode account for 1,200 rounds. The
calibrated arm makes two evaluator-side calls per round and the standard arm
makes one.

## Missing evidence

- `experiments/calibrated_ttrl.json`: absent.
- Length-normalized control: absent from the driver and result package.
- Symmetric-LR control: absent from the driver and result package.
- Seed-level records for 20--49 percent gamma and 45--67 percent JSD: absent.
- Raw confidence records for the 31 percent and mean-confidence statements:
  absent.
- Model identity: the driver uses `deepseek-chat` and `gpt-4o`; the manuscript
  names DeepSeek-V4-Pro and GLM5.2.

## Citations

All 17 citation keys resolve to 17 unique embedded BibTeX items. This is a
mechanical parse only; semantic support was not certified.

## Merge evidence

The current calibration-landscape source contains the P9 marker at line 755
and classifies `tmlr-p9/p10 calibrated-TTRL` as a protocol deposit. The
`b1de3c...` snapshot exists and matches its expected hash, but it does not
contain an explicit P9 marker. It cannot prove that the merge itself completed.
