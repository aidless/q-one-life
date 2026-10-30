# A4 threshold and interface semantics

This experiment tests independent review finding A4 against the pinned native
`tools/bench-noise-floor/audit.py`. It asks three interface questions:

1. Is the declared margin `delta` a CLI parameter?
2. How is a point margin equal to `delta` classified?
3. Does a margin confidence interval crossing zero change the verdict?

The frozen runner creates deterministic synthetic fixtures and invokes the
unmodified native tool as a subprocess. It also exercises domain-mismatch,
two-generator floor, and unresolved-gold paths to show that refusal branches
remain fail-closed.

Accepted output:

- `results/run-1.json` and `results/run-2.json` are byte-identical.
- Their SHA-256 is
  `d2fedc88b0ae81f782c8169cfe8c66103871a389db644476a4b47735e049727c`.
- All five preregistered gates pass.

The result is narrow. It establishes that the pinned CLI hard-codes 2.0 points,
that a derived equality fixture is returned as `READABLE` while the candidate
manuscript instructs a reader to treat equality as `MARGINAL`, and that a point
margin of `+13.6364` with a paired interval `[-100.0000, +21.1240]` is still
returned as `READABLE`. It does not establish ranking validity, close the
independent review, resolve MDE terminology, or authorize an arXiv upload.
