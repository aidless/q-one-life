# Independent Proof Audit — Paper 2 (Conditional Coupling Bound)

- **Audit date:** 2026-10-30
- **Auditor:** Independent (numpy numerical verification, not paper's code)
- **Audit scope:** All theorems/propositions in the v9 theory hierarchy + the 3
  propositions stated in the manuscript body.
- **Audit method:** Each theorem's key inequality steps were verified numerically
  over random parameter configurations. Where a step failed, the root cause was
  diagnosed and the failing condition characterized.

---

## Verdict Summary

| Theorem | Location | Verdict | Finding |
|---------|----------|---------|---------|
| Prop. coupling-precision | body §5 (line 116) | **PASS** | Standard CR bound; I_1 = s(1−s) correctly derived |
| Prop. proxy-var | body §5 (line 133) | **PASS (with caveat)** | Delta-method variance correct; explicitly non-tight for trajectory proxy |
| Prop. impossibility | body §5 (line 165) | **PASS (conditional)** | s(1−s) ≤ 1/4 verified; bound conditional as stated |
| Theorem 1 (Pinsker) | theory/T1 | **FAIL** | TV lower bound + final algebra both incorrect |
| Theorem 2 (Cramér–Rao) | theory/T2 | **FAIL** | Fisher matrix rank-1; (γ,H) not jointly identifiable |
| Theorem 5 (Minimax) | theory/T5 | **PARTIAL** | Asymptotic Θ correct; KL bound uses non-standard σ |
| Theorem 6 (PAC-Bayes) | theory/T6 | **UNVERIFIED** | Requires KL decomposition assumptions |
| Theorem 7 (Polytope) | theory/T7 | **UNVERIFIED** | Geometric; depends on T3 validity |
| Theorem 8 (Reversal) | theory/T8 | **UNVERIFIED** | Depends on T5 + posterior collapse |

---

## Detailed Findings

### 1. Theorem 1 (Pinsker) — FAIL

**Statement:** H(w*) ≤ H_max − 2(log2)·Δr²/(4τ² + Δr²)

**Audit result:** The final bound is **violated on 2863/3000** random configurations
(95.4% failure rate). Example: K=2, τ=2.357, Δr=2.261 gives H=0.590 vs bound=0.434
(excess +0.156 bits).

**Two independent errors in the proof:**

**(a) Step 3 TV lower bound is wrong.** The proof claims
  TV(w*, u) ≥ [Δr/τ / (2(1 + Δr/τ))]·(K−1)/K.
  Numerical audit: **5799/10000 violations**. Example: K=3, τ=2.627, Δr=0.539 gives
  TV=0.0357 vs claimed=0.0568. The claimed bound **overestimates** the true TV.

**(b) Final algebraic step has reversed direction.** The proof claims
  (Δr/τ)²/[8(1+Δr/τ)²] ≥ 2log2·Δr²/(4τ²+Δr²).
  Numerical audit: **50000/50000 violations** (100%). Example: τ=1.023, Δr=4.748
  gives A=0.085 vs B=1.169 (A is only 7% of B). The inequality is **reversed** —
  the proof cannot conclude H ≤ log K − B from H ≤ log K − A when A < B.

**Root cause:** The TV lower bound (a) is too weak, and the subsequent algebra (b)
reverses the inequality. Together they make the stated entropy upper bound false.
The theorem statement is **not supported by its derivation**: the two errors
above jointly prevent the entropy upper bound from following.

---

### 2. Theorem 2 (Cramér–Rao) — FAIL

**Statement:** Σ_θ̂ ≥ I(θ)⁻¹ for θ = (γ, H) under a logistic observation model.

**Audit result:** The regularity condition (ii) "model is identified, i.e., I(θ)
positive definite" **fails for this model**.

**Diagnosis:** With σ(γ,H) = (1+αγ)(1−H/K), the Fisher matrix is
  I = N/(s(1−s)) · [[(ds/dγ)², (ds/dγ)(ds/dH)], [(ds/dγ)(ds/dH), (ds/dH)²]]
This is the **outer product** of the score vector (ds/dγ, ds/dH), hence
**rank-1** for all parameter values. The determinant is identically zero:
  det(I) = N²/(s²(1−s)²) · [(ds/dγ)²(ds/dH)² − (ds/dγ)²(ds/dH)²] = 0.

**Consequence:** (γ, H) are **not jointly identifiable** from Bernoulli
observations under this model — only the product (1+αγ)(1−H/K) is identifiable.
The joint 2×2 Cramér–Rao bound does not apply.

**Additional issue:** σ(γ,H) = (1+αγ)(1−H/K) is **not a valid probability**
when αγ > 1 (e.g., γ=1.5, α=1: σ=2.39 > 1). The model is ill-posed at large γ,
consistent with the manuscript's own admission that the logit estimator is
biased as γ→0 and the Delta method degrades for γ ≥ 1.

---

### 3. Theorem 5 (Minimax) — PARTIAL

**Statement:** inf_θ̂ sup_θ E‖θ̂−θ‖² ≥ c_min^(minimax)(δ)/N with
c_min = δ·γ_max²·σ(1−σ)/16.

**Audit result:** Asymptotically correct (Θ form) via Le Cam + Fano, **but**
the Step 2 KL bound `D_KL(θ_i‖θ_j) ≤ (Δσ)²/(σ(1−σ))` uses a non-standard
representative σ and has **3775/100000 violations** (3.8%). The standard form
`D_KL ≤ (Δσ)²/(s₂(1−s₂))` passes 100%. Recommend replacing the KL bound with
the standard denominator form for rigor.

---

### 4. Propositions in the manuscript body — PASS

- **coupling-precision (line 116):** I_1(γ) = s(γ)(1−s(γ)) correctly derived
  from s′(γ) = s(1−s). Standard Cramér–Rao. **Sound.**
- **proxy-var (line 133):** Delta-method variance expressions correct. The
  non-tightness for the trajectory proxy is correctly identified and stated.
  **Sound with explicit caveat.**
- **impossibility (line 165):** The chain CV ≥ 1/(γ√(Ns(1−s))) ⇒
  γ·H·CV ≥ H/√(Ns(1−s)) ≥ 2H/√N ≥ 2h_min/√N uses s(1−s) ≤ 1/4, verified
  numerically over all s∈[0,1]. The conditional framing (requires unbiased
  regular γ̂, H ≥ h_min) is appropriate. **Sound, conditional.**

---

## What This Means for the Paper

1. **Theorem 1 is not supported by its derivation** — the TV bound and the final
   algebra step both fail numerically. It should not be cited as a proof without
   correction.
2. **Theorem 2's joint CR bound is ill-posed** — (γ,H) are not jointly
   identifiable under σ = (1+αγ)(1−H/K). The CR analysis must be restricted to
   a single identifiable parameter (the product), or the model must be changed.
3. **Theorem 5 is asymptotically sound** but needs the KL bound fixed to the
   standard form.
4. **The three propositions in the body are sound** (with the stated caveats),
   which is consistent with the manuscript's careful conditional framing.

## Recommendation

The v9 theorem hierarchy (T1–T8) does not currently support the manuscript's
theory claims. The **independent proof audit found Theorem 1 and Theorem 2
contain mathematical errors** that invalidate the stated forms. Advancing the
paper requires either (a) corrected derivations, (b) weakened statements that
match what is actually provable, or (c) removal from the theory section with
the corresponding claims downgraded.

This audit was performed by independent numerical verification (numpy random
configurations), separate from the paper's own derivation and code.
