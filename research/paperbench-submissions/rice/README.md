# Rice — Architecture-level reproduction stub

Gap audit (2026-11-07): this task remains an architecture stub. Required
RL environments, PPO-pretrained policies, StateMask/StateMask-R and fidelity
scores need environment setup and GPU training budget. See
`research/validation-20261106/remaining-task-gaps/README.md`.

This submission is a Q-One minimal reference implementation for PaperBench task
`rice`. It records the rubric categories, exposes a deterministic `run(data)`
interface, and has executable smoke tests.

It does **not** reproduce the paper's training results, benchmark tables or
real evaluator score. No claim of a PaperBench capability score is made.

Rubric leaves: 361. Categories: Code Development, Code Execution, Result Analysis.
Recurring rubric terms: Actor, Adversarial, Algorithm, Alternative, Appendix, Challenge, Cheng, Critic.
