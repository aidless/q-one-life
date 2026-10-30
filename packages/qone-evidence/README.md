# qone-evidence

A minimal, dependency-free claim ledger. Every claim can bind evidence files by
SHA-256, and verification re-hashes those files to detect drift.

```python
from qone_evidence import register_claim, bind_evidence, verify_ledger, render_report

register_claim("ledger.json", "C01", "The sample contains 30 tasks.")
bind_evidence("ledger.json", "C01", "evidence/analysis.json", field="n_tasks")
print(verify_ledger("ledger.json"))
print(render_report("ledger.json"))
```

Verification fails closed: a missing file, a changed hash, or a `verified` claim
with no evidence all produce errors. Nothing is executed and no claim is
upgraded automatically.
