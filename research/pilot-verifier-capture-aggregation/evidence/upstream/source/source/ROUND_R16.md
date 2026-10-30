# Revision Round R16 — PAPER6

Date: 2026-08-19

## Scope

Convert PAPER6 from a skeleton with unsupported real-LLM and universal claims
into an evidence-scoped synthetic benchmark plus local pilot. Establish the
canonical evidence package, claim ledger, and reproducibility protocol.

## Changes

| ID | File | Change | Reason | Evidence impact | Status |
|---|---|---|---|---|---|
| CHG01 | `evidence/` | Copied main, pilot, and local-pilot JSON into canonical subdirectories. | Prevent accidental use of stale or fabricated sources. | Manifest now covers canonical files. | done |
| CHG02 | `CLAIM_LEDGER.md` | Added claim-level provenance and blocked claims. | Enforce evidence-first drafting. | Universal theorem/generalization claims no longer admissible. | done |
| CHG03 | `WORKING_NOTES.md`, `evidence/protocol.md` | Recorded scope, exclusions, and missing provenance. | Make limitations auditable. | Local pilot is descriptive only. | done |
| CHG04 | `main.tex` | Tightened abstract language to match available synthetic and pilot evidence. | Remove unsupported pre-registered/full-real claims. | Numerical claims remain traceable. | done |

## Remaining blockers

Theorem 2 proof, formal confidence intervals/multiplicity, public citation
records, environment/model provenance, and held-out real-trace validation remain
open. This round therefore does not certify Strong Accept.
