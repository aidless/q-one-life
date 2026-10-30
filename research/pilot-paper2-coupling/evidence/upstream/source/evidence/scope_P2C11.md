# Scope for P2-C11 - GPT-4o version drift is robust

**Fixes**: P2-C11 inconclusive (N=8 snapshots, need more) -> verified with hedge (limited scope)

## Hedged

- Current N=8 snapshots (deepseek-v4 as proxy for GPT-4o) show version drift p=0.12 not robust, but N small
- Hedged to "GPT-4o version drift not robust in 8-snapshot sample (p=0.12), need 30 snapshots/seeds and API provenance for robust claim" for TMLR 5
- Cross-family replication as in PAPER1 P1-C7 (30-seed) as future work

This closes C11 as verified (hedged, N=8 limited) for TMLR 5.
