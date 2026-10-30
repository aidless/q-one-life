# Research Factory Evidence Integration Receipt

This document confirms integration of the following artifacts into the Q-One research portfolio evidence chain. All hashes verified and reproducible as of 2026-10-28T13:45Z.

## Noise Floor Producer-Baseline Counterexample

**Experiment ID**: `noise-floor-producer-baseline-necessity-counterexample`  
**Status**: reproduced  
**Byte-identical runs**: true  

### Critical Result
- **Producer floor**: 1.0 (three perfect producers)
- **System scores**: A=0.9, B=0.5
- **Single-item deletions stable**: 700/700
- **Paired discordance**: 280 vs 0
- **Gate verdict**: refused despite deterministic, stable ordering

### Positive Control
- **Producer floor**: 0.8
- **System scores**: A=0.9, B=0.5
- **Gate verdict**: readable (as expected)

### Negative Control
- **Ordering reversed**: A<B
- **Gate verdict**: refuses A>B, recognizes direction reversal

### Failed Attempts (preserved, not accepted as evidence)
- Attempt 1: implementation error before measurement
- Attempt 2: incorrect positive-control floor
- Attempt 3: incorrect paired discordance derivation

### Scientific Conclusion (narrow)
The declared producer-baseline gate can refuse a top ordering that is deterministic and stable under every single-item deletion. Therefore clearance of that gate is **not a necessary condition** for every resolvable top ordering, and the gate cannot by itself be read as a general ranking noise bound.

### Interpretation Limits
- This is a synthetic logical witness, not a study of real leaderboard prevalence.
- Does not show the producer floor is uninformative in all settings.
- Does not establish the manuscript's publication readiness.
- Does not replace an external gold-pool study for the manuscript's empirical claim.

## Source Lineage Recovery

**Commit**: `9eb77f1b77baaa9932d8faf18da2fc50a2077f6c`  
**Manifest source SHA-256**: `0d68bda378fa0fc4fe1d39c8c8d46ba39052230fae7a1e8f2fd44b41e5b7e113`  
**Current manuscript SHA-256**: `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca`  
**Diff**: +8 lines, -5 lines  
**Lineage valid**: true  
**Publication identity ready**: false  

### Note
Exact manifest-named source is recovered from git commit. Current file is retained as a lineage revision, not silently relabeled. Publication identity, author, license and upload authorization remain separate gates.

## Research Factory Verification Summary

**Verification generated at**: `2026-10-28T13:37:25.603077Z`  
**Command**: `PYTHONPATH=/tmp/qone-research-test-paths-143a9e473b7d/qone-life-src:/tmp/qone-research-test-paths-143a9e473b7d/q-one-core-src:/tmp/qone-research-test-paths-143a9e473b7d/q-one-agent-src /home/liuzewen/.cache/qone-life-venv/bin/python '/home/liuzewen/F:\\deepseek/q-one-life/scripts/research_factory_verify.py'`

### Test Results
- **pytest**: 92 passed, 1 warning, 22 subtests
- **unittest**: 90 passed, 4 resource warnings
- **Ruff**: passed
- **JSON Schema**: 28 checked, passed
- **Project validation**: 17 valid, 0 ready
- **Claim ledgers**: 17 pilots, all passed

### Noise Floor Pilot Status
- **Valid**: true
- **Ready**: false
- **Blocked claims**: C02 (source identity), C03 (independent review)
- **Verified claims**: C01, C05–C10
- **Candidate claims**: C04 (external leaderboard study)
- **Plan stages**: source-identity=blocked, scientific-review=blocked, evidence-recomputation=verified

### Notes
- Unknown readiness remains null; no aggregate quality score is produced.
- Compilation and packageability do not establish scientific readiness.
- No upload, account action or publication occurred.
- The producer-baseline counterexample is a synthetic logical witness, not an external leaderboard study.
- Noise Floor still has blocked source-identity and scientific-review claims; it is not arXiv-ready.

## Resume Evidence Integration

**Evidence SHA-256**: `1564b35ac3ee9d7c9862d01d81afb3f2baabc29fa4fc6c79693af4486d1b7bf2`  
**Artifacts checksummed**: 41 files (including research factory outputs, source lineage, counterexample, and cleanroom logs)  
**Checksum verification**: all OK

### Non-claims
- The benchmark is a six-task local engineering acceptance check.
- It is not an external validity study, user study, or benefit claim.
- The working SQLite database is not end-to-end encrypted.
- The current desktop artifacts are unsigned internal builds.
- No paper is publication-ready or uploaded.
- The producer-baseline counterexample is a synthetic logical witness, not an external leaderboard study.
- Noise Floor still has blocked source-identity and scientific-review claims; it is not arXiv-ready.

---

Generated at: 2026-10-28T13:45Z
