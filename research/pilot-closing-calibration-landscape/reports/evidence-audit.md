# Evidence audit

Status marker: `agent-proposed, not human publication approval`

## Reproduces

- Simulation gamma means: 0.143, 0.719, 0.574 from 15 checkpoint seeds.
- Real-API standard arm: matches the separate final-results uncalibrated block.
- Carrier rows: 11/11.
- Citation keys: 26/26.
- Clean-room compile: 10 pages, deterministic PDF.

## Does not reproduce

- CV values 0.192, 0.134, 0.174 from per-seed gamma or entropy.
- The real-API CG and CG+TEE arms: 15/15 seeds are `gamma=0, H=1`.
- N=15 model identity or parser-success data.

## Attribution

The separate final-results means are 0.991 (uncalibrated), 0.602 (calibrated),
and 0.644 (CG+TEE). The 39.249 percent reduction is uncalibrated versus
calibrated. CG+TEE is 0.0419 above calibrated, so the 39.2 percent scalar is
not a CG+TEE result.

## Gate

The analysis is sufficient for a bounded reproducibility failure report. It is
not sufficient for a mitigation claim, a TEE null claim, arXiv readiness, or
publication.
