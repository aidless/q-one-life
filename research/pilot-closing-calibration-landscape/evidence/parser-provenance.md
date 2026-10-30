# Parser provenance

Status marker: `agent-proposed, not human publication approval`

The real-API runner sha256 is
`451d17dcba4c2cf588f9220b0dc3276927c61be15aaac5d570750a75cdb16683`.
Its confidence parser attempts `float(resp.strip().split()[0])` and returns
`0.5` in the exception path. With the additive update
`alpha * (2c - 1)`, a fallback value of `0.5` produces exactly zero update.

The archived result writer stores only the completed-seed map. The N=15 JSON
files contain no executor/evaluator identity, endpoint, model version, parser
attempt count, or parser-failure count.

The fixed local smoke script has sha256
`9f00e9df4bbf2eb2e20fadab608cc2f95757b8c29bfc8d48fd1866d12ffb1d35`.
Its 3-seed, 10-round smoke run records zero confidence parse failures and
non-degenerate gamma/entropy checks. This is a protocol feasibility signal, not
an N=15 result.

No credentials, authentication headers, or account values are copied into this
overlay.
