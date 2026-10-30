# Q-One research overlay: Calibrating the Evaluator

Status marker: `agent-proposed, not human publication approval`

- Family: `qf-calibrating-the-evaluator-does-probabili-6544cd664a`
- Project: `qp-tmlr-tmlr-p9-a9f202b5304f`
- Disposition: `merge_archive`
- Project status: `archived`
- Independent package: none by design
- Uploaded: no

## Canonical evidence

- Canonical overlay copy: `evidence/upstream/main.tex`
- SHA-256:
  `e9487a094e1377549572faaa207cdff9f0f99a72d8903518186dac3a953e3d03`
- Existing arXiv identity: `2606.31371v1`
- Published title matches the local title.
- Listed author: Zewen Liu.

The raw arXiv API response and headers are retained under `evidence/`.

## Why this is merged and archived

The current manuscript-scale paragraph and result table describe an experiment
larger than the archived driver. The driver realizes 1,200 rounds, 2,400
executor calls, and 1,800 evaluator calls, while the manuscript prints 2,400
rounds and 3,600 evaluator calls. The two claimed controls are absent from the
driver. The expected per-seed result file,
`experiments/calibrated_ttrl.json`, is absent. The driver calls
`deepseek-chat` and `gpt-4o`, not the manuscript's DeepSeek-V4-Pro and GLM5.2.

The current calibration-landscape merge source explicitly marks P9 as an
Appendix B protocol deposit. That supports archival consolidation, not an
independent empirical claim.

## Boundary

No result percentage, mechanism statistic, or control conclusion is promoted
as verified. The arXiv record proves identity only. It does not prove
reproducibility, scientific readiness, or permission to upload a revision.
