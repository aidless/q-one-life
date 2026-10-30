# Independent review request: Noise Floor candidate R3

Review type: method, construct validity, statistics, and executable-contract
audit. This packet requests review only. It does not authorize an arXiv upload,
account action, author or licence change, or any claim that R3 is accepted.

## Frozen target

- Project: `research/pilot-bench-noise-floor`
- Candidate: `revisions/2026-10-29-support-threshold-r3`
- Candidate source SHA-256:
  `a9eef802faa6ef80f7916626a28aade11f1922701fb1f3b24b2f3780a69e0bb6`
- Candidate manifest and checksum inventory: `revision-manifest.json` and
  `SHA256SUMS.txt`
- Parent candidate R2 source SHA-256:
  `fc24f8effef7c6f90c6dca6a52ea967adcec60bf7b79408c817b3a8561930c0f`
- Canonical overlay source SHA-256:
  `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca`
- Native-manifest source SHA-256:
  `0d68bda378fa0fc4fe1d39c8c8d46ba39052230fae7a1e8f2fd44b41e5b7e113`
- Earlier independent review SHA-256:
  `8d815000775ad110354043854967c79044605deb1f6113a549a6cba13078c86e`

The canonical source still differs from the native-manifest source. R3 is a
separate candidate and does not rewrite either file, so publication identity
remains open.

## Why R3 exists

The earlier independent review raised four method issues, A1-A4. R3 is built on
R1 and R2 and integrates reproducible work on all four while keeping unresolved
parts visible:

| Finding | R3 state | Evidence | Still open |
|---|---|---|---|
| A1 producer baseline is not a ranking-noise bound | Claim narrowed with a synthetic counterexample; not independently accepted | `experiments/producer-baseline-counterexample/` | Whether narrowing is sufficient, or an external disjoint-gold study is required; C03 |
| A2 zero margin and non-zero bootstrap interval are different estimands | Separated as `theta_both` and `theta_fixed`; native factuality output reproduced | `experiments/bootstrap-estimand-a2/` | Independent acceptance of the estimand labels |
| A3 k-fold LOO comparison leaked support | Recomputed all arms on one joint support; LOO becomes exactly zero and a k-fold control remains positive | `experiments/kfold-common-support-a3/` | The 54-item preference arm is descriptive; this is not a ranking-validity result |
| A4 rule, statistics, and implementation disagree | R3 states the executable `leader - floor >= 2.0` policy, equality arm, and non-gating interval; fixtures bind the pinned tool | `experiments/threshold-interface-a4/` | MDE terminology, generator-independence interpretation, and external validity |

## Required evidence

Verify first:

```bash
cd '/home/liuzewen/F:\deepseek/qone-life/research/pilot-bench-noise-floor/revisions/2026-10-29-support-threshold-r3'
sha256sum -c SHA256SUMS.txt
```

Then read:

1. `revision-manifest.json` and `REVISION_R3.md`
2. `source/main.tex`, `main.diff`, and `main-vs-canonical.diff`
3. `evidence/README.md`, `evidence/paper-ledger-overlay.json`, and
   `evidence/verdict-claims-overlay.json`
4. `reports/package-audit.json` and `reports/cleanroom/receipt.json`
5. `reports/ledger-reverse-coverage.json`,
   `reports/ledger-anchor-census.json`,
   `reports/verdict-word-gate.json`, and
   `reports/candidate-gates-summary.json`
6. A3: `experiments/kfold-common-support-a3/preregistration.json`,
   `run_common_support.py`, `results/reproduction.json`, and
   `results/REPORT.md`
7. A4: `experiments/threshold-interface-a4/preregistration.json`,
   `run_threshold_interface.py`, `results/reproduction.json`, and
   `results/REPORT.md`
8. `evidence/REVIEW_INDEPENDENT_2026-10-24.md` and
   `evidence/source-lineage.json`
9. `CLAIM_LEDGER.md`, especially blocked C02/C03 and candidate C04

The candidate receipts establish mechanical integrity only: 11-file package
audit, two-run deterministic 46-page compile, 355 reverse readings with 352
bound, 3 excused and 0 unbound, a GREEN anchor census with 0 missing anchors,
and 137/137 verdict-word checks. They do not prove scientific validity.

## Review questions

1. **A1 construct:** Does R3 consistently describe the producer-baseline
   construction as an audit of consensus labels and not as a bound on ranking
   noise? Identify every sentence that still overreaches.
2. **A1 evidence sufficiency:** Can the narrowed claim be accepted from the
   preserved synthetic witness and existing measurements, or does it require
   a real leaderboard with gold labels produced independently of the ranked
   systems? If new evidence is required, specify the minimum sampling design.
3. **A2 estimand:** Are `theta_both` and `theta_fixed` distinguished correctly,
   and does R3 avoid using the fixed-winner interval as uncertainty for the
   zero identity?
4. **A3 support:** Is the joint main-gold, LOO-gold, fold-gold and actor support
   the right common domain for the comparison? Does the 54-item preference arm
   remain clearly descriptive rather than inferential?
5. **A4 executable contract:** Verify that R3 matches the pinned
   implementation: hard-coded `delta = 2.0`, equality classified `READABLE`,
   and the confidence interval printed but not gating the decision. Flag any
   remaining mismatch.
6. **A4 terminology and independence:** Is the interval half-width still being
   called an MDE beyond what its construction supports? Does R3 still imply
   that `m >= 3` supplies independent reproduction or accuracy when it only
   removes one exact two-vote degeneracy?
7. **New defects:** Did the A3/A4 integration introduce contradictions,
   unsupported claims, incorrect numbers, broken cross-references, or stale
   historical wording?
8. **Disposition:** State whether R3 is ready for the next internal round,
   requires a specific revision, or is blocked on external evidence.

## Output contract

- Produce a read-only report with severity, exact file and line/section
  location, finding, evidence, and one requested revision per finding.
- Bind the report to the frozen R3 source SHA-256 above.
- Separate verified mechanical facts from judgment calls and missing evidence.
- State explicitly whether each of A1, A2, A3, A4 is closed, narrowed, or open.
- End with one disposition: `pass`, `minor-revision`, `major-revision`, or
  `blocked`.
- Do not modify the manuscript, manifest, receipts, project state, accounts,
  authors, licence, or external services.
- A `pass` disposition is a review result for R3 only; it is not arXiv
  authorization or permission to replace the canonical source.
