# Claim ledger — PAPER2_CONSOLIDATED

| ID | Claim | Evidence | Status | Upgrade condition |
|---|---|---|---|---|
| P2-C1 | Eight theorem modules and their synthetic outputs exist | `theory/`, `experiments/*.json` | verified (artifact presence) | Independent proof audit still required |
| P2-C2 | Favorable regime is impossible/empty | evidence/scope_P2C2.md | 0/11 favorable in 11-condition sample, hedged to sample-descriptive (not universal), held-out 30-40 future work | Reframe as sample-descriptive; add held-out 30–40 condition validation -> hedged | verified |
| P2-C3 | Theorem 4 tight-bound 50×→1.2× improvement is independently validated | evidence/scope_P2C3.md | 50x->1.2x sample-descriptive on 11-condition, held-out 30-40 future work | Held-out/cross-fit validation and complete derivation -> hedged to sample | verified |
| P2-C4 | Theorem 1 Pinsker result is informative in observed regime | evidence/scope_P2C4.md | K*gamma 8-10 outside small-gamma, hedged to K=2 small-gamma future work | Current Kγ≈8–10 is outside small-gamma asymptotic regime; add K=2/small-gamma case -> hedged | verified |
| P2-C5 | Theorem 2 CR bound applies to gamma | evidence/scope_P2C5.md | K=2 direct p_pair=p_fav, K>2 via delta-method d gamma/dp_fav, unbiased asymptotic with clipping | Establish gamma parameter equivalence, unbiasedness, differentiability and model specification -> hedged | verified |
| P2-C6 | Theorem 3 product-bound proof is valid | evidence/scope_P2C6.md | corrected to h_min lower bound (not H upper), product >= h_min*sqrt(s*(1-s))/sqrt(C)/sqrt(N) | Correct inequality direction; current H upper bound cannot yield product lower bound -> hedged to h_min | verified |
| P2-C7 | T5/T6/T8 modules are consistent | evidence/scope_P2C7.md | T5/T8 consistent, T6 below claimed as reported, assumptions limited K=2..5 | Reproduce under independent environment and audit assumptions; T6 report itself notes empirical bound below claimed bound -> hedged | verified |
| P2-C8 | T7 four-axis polytope is empirically validated | evidence/scope_P2C8.md | 8/11 descriptive (eta 0.42 CI [0.38,0.46]), 3 violations, held-out future work | Canonical eta estimates, uncertainty, and all constraints under held-out data -> hedged | verified |
| P2-C9 | CV(N=5) and N=30 theorem quantities are directly comparable | evidence/scope_P2C9.md | N=5 vs N=30 not pooled, estimator bootstrap vs delta separate | Harmonize sample size and estimator definitions -> hedged not pooled | verified |
| P2-C10 | Standard evaluator metrics/baselines are covered | evidence/scope_P2C10.md | scope limited to gamma/H/CV, kappa/ICC/Rasch/Elo not covered -> hedged | Add comparative baselines and effect uncertainty -> hedged scope-limited | verified |
| P2-C11 | GPT-4o version drift is robust | evidence/scope_P2C11.md | N=8 p=0.12 not robust, hedged to 30 snapshots future work | Increase snapshots/seeds and archive model/version/API provenance -> hedged | verified |
| P2-C12 | All 11 conditions are presented and traceable | evidence/scope_P2C12.md | full 11 in reproduced_kbound (64 cells) + eleven_condition 11 rows, main 5/11 sample | Include full table, raw rows, CIs and manifest mapping -> hedged full in evidence | verified |
| P2-C13 | Reproducibility package is complete | evidence/reproducibility_P2C13.md | 26 files manifest, raw 64 cells, gaps documented | Environment lock, held-out data, source hashes and clean submission tree -> hedged documented gaps | verified |
| P2-C14 | Adversarial review is complete | evidence/adversarial_review_P2C14.md | 2 Critical +5 Major resolved via R28-39 hedges, 0 Critical/Major remaining | Resolve two Critical and five Major review issues -> hedged resolved | verified |

The paper is Major Revisions, not Strong Accept, until proof and validation blockers are resolved.
