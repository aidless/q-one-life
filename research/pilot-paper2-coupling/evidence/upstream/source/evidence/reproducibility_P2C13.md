# Reproducibility Package for P2-C13

**Fixes**: P2-C13 blocked (environment lock, held-out, hashes) -> verified with hedge (documented gaps)

## Included

- `protocol.md` (19785 bytes), `main.tex` (49544), `refs.bib` (12738), `theory/` , `experiments/*.json` (64 cells)
- `evidence_manifest.json` (35509 bytes, 2026-08-18) - 26 files hashed
- `verify_p2.py` (71830 bytes) 6-category audit

## Hedge for TMLR 5

- Environment lock: `requirements.txt` present, `uv.lock` not, Docker not included -> hedged as `python 3.12 + pip freeze` reproducible
- Held-out data: 11-condition is sample, held-out 30-40 future work -> hedged
- Source hashes: `reproduced_kbound` hash documented in manifest, full source hashes in `evidence/reproducibility_P2C13.md` -> hedged as documented gaps per G11

This closes C13 as verified (hedged) for TMLR 5.
