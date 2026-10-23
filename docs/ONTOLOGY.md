# Personal ontology

The life layer separates three kinds of records:

1. **Observation** — a value recorded at a time with a user-defined range and source.
2. **Metric specification** — the meaning, range, weight, and target count used to interpret an observation.
3. **Review** — a generated prompt that exposes coverage, missingness, and questions for the next cycle.

Domains are labels chosen by the user. The examples use energy, learning, work, and recovery, but the software does not assume those domains are complete or universally important. A future UI can add relationships, finance, health, creativity, or any other domain while keeping the same record shape.

A `decision_id` is an optional reference to a record in `q-one-core`. It is a link, not a copy of the decision context. This keeps personal observations in the life repository and lets the core ledger remain provider-neutral.
