# One Rung at a Time: Attributing an ARC-AGI-3 Submission When the Offline Ruler Cannot Select Arms

## Abstract

This report studies attribution in an interactive competition where the submitted agent is evaluated on hidden games. We retain a three-submission lineage, pin its notebook bytes, and separate observed leaderboard differences from demonstrated component effects. Scores were 3.38, 4.01, and 4.24. The latter two submissions changed a per-game time limit and prefix caching, respectively. These are single observations, without a measured noise distribution. They establish a reproducible configuration lineage, but do not establish causal gains. We also correct two interpretation errors: partially completed games can receive credit, and an offline completion measure cannot be converted directly into the official action-efficiency score. Repeated visible-game evaluation and hidden scoring answer different questions; both need explicit records.

## 1. Task and scoring

ARC-AGI-3 measures completed levels and action efficiency relative to human baselines. Its per-level efficiency term is quadratic in the human-to-agent action ratio, with a per-level cap. Game scores also depend on which levels were completed; completing only part of a game can earn a nonzero score. The final score is bounded by 100%. Our previous statement that all partial progress scores zero was incorrect. See the [official scoring methodology](https://docs.arcprize.org/methodology).

This distinction matters for experiment design. Completion counts, action counts, and official scores should be retained separately. A policy can complete more levels while using enough additional actions to lose efficiency. Conversely, an improvement in action efficiency does not demonstrate improved general reasoning.

## 2. Byte-pinned configuration lineage

The substrate is the Duck/TAAF harness and the public Flash-Next recipe. Credit for that infrastructure belongs to its original authors, including Jeroen Cottaar and Tufa Labs. Our evidence concerns subsequent configuration changes, not authorship of the underlying model or harness.

| Submission | Notebook | Change recorded relative to parent | Public score |
|---|---|---|---:|
| 56637376 | arc3-duck-replica-v1 | Initial replicated configuration | 3.38 |
| 56656333 | arc3-duck-7450-v1 | Per-game limit 7920 to 7450 seconds | 4.01 |
| 56691079 | arc3-duck-prefcache-v1 | Prefix caching enabled | 4.24 |

The authenticated submission receipts identify the source version, configuration change, and source SHA-256. A fresh pull of the 4.24 notebook matches its recorded hash, `e53788bed53c014951342d9c2517ee59137cfe820f73084f3892268c9be0bdc4`. The audit retains the corresponding parent files and checks their recorded hashes independently.

The arithmetic differences are +0.63 and +0.23. They are observed score differences, not uncertainty-adjusted estimates. Host-side sampling, serving behavior, task allocation, or game variation could contribute. The six agent-loop repairs already present in the replicated configuration have not been isolated by this ladder, so these differences cannot be attributed to those repairs.

The accompanying [public evidence notebook](https://www.kaggle.com/code/liuzewen123/arc-paper-track-evidence) is a compact record of the experiment. Recomputing recorded digests is weaker than independently hashing all original source bytes: the competition notebooks remain private. We disclose that access limitation rather than treating a digest printed in a notebook as independent proof of the whole lineage.

## 3. Offline evaluation and hidden scoring

The visible offline environment contains a fixed public game set. The hidden run obtains its available games from the live competition gateway. The populations can therefore differ. The local harness also exposes completion statistics that do not have the same units as the official efficiency score. A ratio between an offline completion percentage and a leaderboard score is not a calibrated performance estimate; we withdraw the earlier proposed response ratio.

This does not prove that every offline improvement is useless for hidden model selection. It means that such predictive validity has not been demonstrated by this experiment. Visible runs remain useful for detecting crashes, repeated failures, excessive actions, and changes larger than local run-to-run variation. Hidden scores remain necessary evidence about the competition population. Neither a single local run nor a single hidden score resolves small effects reliably.

The offline parquet emitted for a normal Save & Run is a placeholder. It cannot be read as evidence that the hidden competition has been played. Runtime completion, a valid output file, and successful official scoring are distinct events and are recorded separately.

## 4. Contribution verification and remaining experiments

The next comparison uses repeated runs of the 25 visible games, with the model, harness revision, and serving configuration fixed. Three directions are kept separate: action efficiency, context management, and resource allocation. Each run should preserve per-game completion, action counts, elapsed time, sampling settings, and failures. A branch is expanded only after a measured validation benefit; planned experiments are not reported as completed results.

The same principle applies across competitions: a convenient local score must have a documented relationship to the actual evaluation before it supports a generalization claim.

## 5. Limits and conclusion

The best account score in this lineage is 4.24. It is an intermediate result, not evidence of a final top-five placement or an award. The two configuration changes have one scored observation each. We have no isolated ablation proving the contribution of the bundled agent-loop repairs, and no calibrated mapping from the offline population to the hidden one.

The contribution is an auditable way to state what an iteration actually establishes: pin the submitted bytes, retain the parent and change, preserve failed attempts, and distinguish score arithmetic from causal attribution. Correcting a scoring interpretation and narrowing an unsupported conclusion are part of that record.
