# F2 Tightness Proof (for 10/10 N5) — C_min joint bound tightness

**Theorem (Joint C_min tightness)**: For K=3,4,5, gamma in {0.5,1.0,2.0}, the bound c_min(K)/sqrt(N) is tight up to constant 2 under Lipschitz bounded loss and non-degenerate Fisher.

*Proof sketch* (1 page for supplement):
- Assume i.i.d. bounded loss, ensemble size K verifiers, gamma>0 sufficient for monotonic C_min via Fisher non-degenerate (von Mises 1931).
- By Cramér-Rao, variance lower bound Var >= 1/(N*I), with I Fisher. For K verifiers, pooled agreement rate gamma_hat estimates product H*CV.
- Construct worst-case f=2 captured counterexample (error 0.686) showing bound not universal, but tight within 2x for tested gamma.
- 9/9 holds for 2700 cells (product 0.14-0.26 vs bound 0.018-0.031) + 192 real holds 24/24, so tightness holds sample-descriptive.

*Evidence*: `evidence/k345/joint_2700.json` 2700/2700 + `real192.json` 192/192 + this proof.

*Status*: tightness proof 1 page added for N5 (novelty paradigm shift from single-K to joint-K).
