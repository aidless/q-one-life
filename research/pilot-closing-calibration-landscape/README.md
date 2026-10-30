# Q-One research overlay: Closing the Calibration Landscape

Status marker: `agent-proposed, not human publication approval`

- Family: `qf-closing-the-calibration-landscape-a-mult-99bef231e5`
- Project: `qp-tmlr-closing-landscape-133137543459`
- Status: `revision`
- Target: `arxiv`
- Package state: `compiled`
- Uploaded: no

## Canonical evidence

- Canonical upstream: `evidence/upstream/paper/main.tex`
- Canonical SHA-256:
  `8314b7b1c2e67eb266bd08c281a4f55fd48c7e920477bae9c9794143f02f3c78`
- Overlay source: `source/main.tex`
- Overlay SHA-256:
  `ada8019e9c9ce01002334c9362dabfade3433ad9b1881be056b139ded32b743d`

The canonical body already withdraws the original 39.2 percent claim, but its
title and several prose passages still imply a TEE effect. The overlay narrows
the title and conclusions to a reproducibility failure analysis.

## What reproduces

- The 15-seed simulation gamma means: 0.143, 0.719, and 0.574.
- The real-API standard arm matches the uncalibrated block of the separate
  final-results artifact.
- All 11 carrier receipts resolve to their JSON locators and printed tokens.
- All 26 citation keys resolve to 26 unique embedded bibliography items.
- Two isolated compiles both produce the same 10-page PDF.

## What is blocked

- The recorded CV values 0.192, 0.134, and 0.174 do not reproduce from
  per-seed gamma or entropy under the tested definitions.
- The real-API CG and CG+TEE arms are `gamma=0, H=1` on all 15 seeds.
- The archived real-API parser silently maps failures to 0.5, producing zero
  additive updates.
- The N=15 result files record neither model identity nor parser success.
- The 39.2 percent scalar belongs to the separate final-results
  uncalibrated-versus-calibrated comparison, not to CG+TEE.
- Independent method/statistics review remains open.

The internal candidate archive is not upload-authorized.
