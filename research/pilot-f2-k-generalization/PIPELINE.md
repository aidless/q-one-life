# Pipeline state

Status marker: `agent-proposed, not human publication approval`

| Stage | State | Evidence |
|---|---|---|
| Source identity | passed | 3 packet variants + 1 mirror; 4 distinct hashes |
| Structure | failed | 17 unique labels and one title/author/end token, but `alg:run` and `lst:runschema` are unresolved |
| Citation parse | passed | 32/32 |
| K=3..5 empirical carrier | blocked | 5 stored rows / 3 conditions / declaration of 2,700 |
| Per-seed consistency | blocked | bootstrap and JSONL means disagree |
| Episode archive | blocked | 180 records; gamma 2.0 absent |
| Real-LLM subset | blocked | 384 archived vs 466 claimed |
| Selective p16 | blocked | provenance fields absent |
| Drift p18 | blocked | protocol has no bound |
| Causal p21 | blocked | protocol has no effect estimate |
| Review | blocked | retained card is reject |
| Candidate package | not started | upstream evidence failed |
| Upload | locked | no package; no authorization |

## Next valid action

Rebuild the K=3..5 run with an archived per-episode file for every condition,
recompute the bootstrap and condition summaries from those rows, restore the
p16/p18/p21 effect carriers, and obtain a new independent review.
