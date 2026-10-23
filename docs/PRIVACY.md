# Privacy and export boundary

Personal observations can reveal routines, health, work patterns, relationships, and financial conditions. The default store is local JSONL with an integrity hash chain, but it is not encrypted and should be protected by the operating system and backup policy.

- Keep `.life-data/` out of public repositories and shared folders.
- Use `export` for a redacted view; it removes notes, decision links, and raw source strings while retaining values and timestamps.
- Review any export manually because even a redacted value can be sensitive.
- Do not send life data to a model provider unless the user has explicitly chosen the provider, retention policy, and fields to share.
- Treat `decision_id` as a cross-repository link that can reveal context when combined with the core ledger.
