# Authoring brief

Status marker: `agent-proposed, not human publication approval`

## Permitted wording

- "The simulation gamma means reproduce from the checkpoint."
- "The CV column is recorded but not reproducible from per-seed fields."
- "The real-API confidence-gated arms are degenerate."
- "The runner silently falls back to 0.5 on parse failure."
- "The 39.2 percent scalar belongs to the separate uncalibrated-versus-
  calibrated artifact."
- "The current package does not identify a TEE bias or noise effect."

## Prohibited wording

- TEE reduces coupling.
- TEE reduces measurement noise or CV.
- The real-API run establishes a null effect.
- The 39.2 percent reduction is a CG or CG+TEE result.
- The N=15 model pair is verified from result data.
- The paper is arXiv-ready, scientifically reviewed, or upload-authorized.

## Required limitation

The paper must state that the CV values lack a per-seed carrier and that the
real-API confidence arms fail the non-degeneracy check. Negative or failure
analysis is acceptable; invented recovery is not.
