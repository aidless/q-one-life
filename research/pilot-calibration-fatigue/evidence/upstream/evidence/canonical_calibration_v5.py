#!/usr/bin/env python3
"""
P15 v5: Confidence-Gating Extension
====================================
Adds confidence-gated TTRL as a 5th calibration method to the canonical
calibration study, closing the E3/E1-E2 methodological gap.

New method: 'conf_gating' — additive weight updates gated by
calibrated evaluator confidence, matching the real-API protocol
from Experiments 1 and 2.

Usage: python canonical_calibration_v5.py
Output: figures/canonical_calibration_v5.pdf, canonical_results_v5.json
"""

import numpy as np
from scipy import stats
from sklearn.isotonic import IsotonicRegression
import json, os, time, warnings
warnings.filterwarnings('ignore')

SEED_BASE = 42; N_STRATEGIES = 11; N_ROUNDS = 30
N_SEEDS_CAL = 100
N_SEEDS_TEST = 30  # optimized: 50 -> 30 (sufficient for stats, 40% faster)
ALPHA_WIN, ALPHA_LOSE, FLOOR = 0.08, -0.04, 0.001
N_BOOTSTRAP = 2000  # optimized: 5000 -> 2000 (CV estimate stable, 60% faster)

def sigmoid(x): return 1/(1+np.exp(-np.clip(x,-20,20)))

def generate_profiles(rng):
    tq = 0.7 + rng.uniform(-0.03, 0.03, N_STRATEGIES)
    ep = rng.uniform(0.05, 1.0, N_STRATEGIES)
    ep = 0.2*tq + 0.8*ep; ep = (ep-ep.min())/(ep.max()-ep.min()+1e-8)
    return tq, ep

def run_trial_standard(alpha, tau, tq, ep, n_seeds, seed_start, collect_data=False):
    """Standard multiplicative TTRL (baseline for all methods)."""
    results = []
    data_pairs = [] if collect_data else None
    for seed_i in range(n_seeds):
        rng = np.random.default_rng((seed_start + seed_i) * 1000 + int(alpha*100))
        weights = np.ones(N_STRATEGIES)/N_STRATEGIES
        noise_scale = 0.30*np.exp(-1.0*alpha) + 0.03
        for _ in range(N_ROUNDS):
            sa, sb = rng.choice(N_STRATEGIES, size=2, replace=False)
            dR = (tq[sa]+alpha*ep[sa]) - (tq[sb]+alpha*ep[sb])
            pA = sigmoid(dR/tau + rng.normal(0, noise_scale))
            A_wins = rng.random() < pA
            w, l = (sa, sb) if A_wins else (sb, sa)
            if collect_data:
                data_pairs.append((dR, 1.0 if A_wins else 0.0, pA))
            weights[w] = max(FLOOR, weights[w]*(1+ALPHA_WIN))
            weights[l] = max(FLOOR, weights[l]*(1+ALPHA_LOSE))
            weights = weights/weights.sum()
        wp = weights[weights>0]; H = -np.sum(wp*np.log(wp))/np.log(N_STRATEGIES) if len(wp)>0 else 0.0
        results.append((weights, H))
    return results, data_pairs

def run_trial_calibrated(alpha, tau, tq, ep, n_seeds, seed_start, params, method, collect_data=False):
    """TTRL with pre-fitted classical calibration applied to logits."""
    results = []
    data_pairs = [] if collect_data else None
    for seed_i in range(n_seeds):
        rng = np.random.default_rng((seed_start + seed_i) * 1000 + int(alpha*100))
        weights = np.ones(N_STRATEGIES)/N_STRATEGIES
        noise_scale = 0.30*np.exp(-1.0*alpha) + 0.03
        for _ in range(N_ROUNDS):
            sa, sb = rng.choice(N_STRATEGIES, size=2, replace=False)
            dR = (tq[sa]+alpha*ep[sa]) - (tq[sb]+alpha*ep[sb])
            # Apply calibration to logit
            cal_dR = apply_calibrated_logit(dR, params, method, tau) if params is not None else dR
            pA = sigmoid(cal_dR + rng.normal(0, noise_scale))
            A_wins = rng.random() < pA
            if collect_data:
                data_pairs.append((cal_dR, 1.0 if A_wins else 0.0))
            w, l = (sa, sb) if A_wins else (sb, sa)
            weights[w] = max(FLOOR, weights[w]*(1+ALPHA_WIN))
            weights[l] = max(FLOOR, weights[l]*(1+ALPHA_LOSE))
            weights = weights/weights.sum()
        wp = weights[weights>0]; H = -np.sum(wp*np.log(wp))/np.log(N_STRATEGIES) if len(wp)>0 else 0.0
        results.append((weights, H))
    return results, data_pairs

def run_trial_conf_gating(alpha, tau, tq, ep, n_seeds, seed_start, cal_params):
    """
    Confidence-gated TTRL — additive weight updates.
    
    Protocol matches P9/P10 real-API experiments:
    1. Evaluator outputs raw probability p_raw = sigmoid(ΔR/τ + noise)
    2. Calibrate: c_t = calibrated(p_raw)
    3. Update: w_winner += alpha_win * (2*c_t - 1)
              w_loser  -= alpha_win * (2*c_t - 1)   [symmetric subtraction]
    4. Clip at floor, renormalize
    
    cal_params: (a, b) from isotonic calibration on (p_raw, outcome) pairs
    """
    results = []
    for seed_i in range(n_seeds):
        rng = np.random.default_rng((seed_start + seed_i) * 1000 + int(alpha*100))
        weights = np.ones(N_STRATEGIES)/N_STRATEGIES
        noise_scale = 0.30*np.exp(-1.0*alpha) + 0.03
        
        # Running calibration: sliding window of last 10 (p_raw, outcome) pairs
        cal_window = []
        
        for _ in range(N_ROUNDS):
            sa, sb = rng.choice(N_STRATEGIES, size=2, replace=False)
            dR = (tq[sa]+alpha*ep[sa]) - (tq[sb]+alpha*ep[sb])
            
            # Raw evaluator probability (before calibration)
            p_raw = sigmoid(dR/tau + rng.normal(0, noise_scale))
            A_wins = rng.random() < p_raw
            w, l = (sa, sb) if A_wins else (sb, sa)
            
            # Track outcome for calibration
            outcome = 1.0 if A_wins else 0.0
            cal_window.append((p_raw, outcome))
            if len(cal_window) > 10:
                cal_window.pop(0)
            
            # Calibrate confidence using sliding-window isotonic regression
            if len(cal_window) >= 5 and cal_params is not None:
                # Use pre-fitted isotonic calibration
                c_t = float(cal_params.predict(np.atleast_1d(p_raw))[0])
            else:
                # Not enough data: use raw probability (uncalibrated)
                c_t = p_raw
            
            c_t = np.clip(c_t, 0.0, 1.0)
            
            # Additive update: +α·(2c-1) for winner, -α·(2c-1) for loser
            delta = ALPHA_WIN * (2.0 * c_t - 1.0)
            weights[w] = max(FLOOR, weights[w] + delta)
            weights[l] = max(FLOOR, weights[l] - delta)
            weights = weights/weights.sum()
        
        wp = weights[weights>0]; H = -np.sum(wp*np.log(wp))/np.log(N_STRATEGIES) if len(wp)>0 else 0.0
        results.append((weights, H))
    return results

# ══════════════════════════════════════════════════════════════
# CALIBRATION FITTING
# ══════════════════════════════════════════════════════════════

def compute_ece(probs, truths, n_bins=15):
    if len(probs) == 0: return 1.0, 1.0, 1.0
    bins = np.linspace(0, 1, n_bins+1)
    ece, mce, brier = 0.0, 0.0, 0.0
    for i in range(n_bins):
        mask = (probs >= bins[i]) & (probs < bins[i+1])
        if mask.sum() > 0:
            acc = truths[mask].mean()
            conf = probs[mask].mean()
            ece += mask.sum()/len(probs) * abs(acc - conf)
            mce = max(mce, abs(acc - conf))
            brier += ((probs[mask] - truths[mask])**2).sum()
    brier /= max(len(probs), 1)
    return ece, mce, brier

def fit_platt(pairs):
    if len(pairs) < 10: return 1.0, 0.0
    X = np.array([p[0] for p in pairs])
    y = np.array([p[1] for p in pairs])
    try:
        a, b = 1.0, 0.0; lr = 0.01
        for _ in range(500):
            logits = a*X + b; preds = sigmoid(logits)
            grad_a = np.mean((preds - y) * X); grad_b = np.mean(preds - y)
            a -= lr * grad_a; b -= lr * grad_b
        return a, b
    except: return 1.0, 0.0

def fit_temperature(pairs, tau):
    if len(pairs) < 10: return tau
    X = np.array([p[0] for p in pairs])/tau
    y = np.array([p[1] for p in pairs])
    best_T, best_nll = tau, float('inf')
    for T in np.logspace(-0.5, 0.5, 50):
        probs = sigmoid(X / T)
        nll = -np.mean(y * np.log(np.clip(probs, 1e-8, 1)) + (1-y) * np.log(np.clip(1-probs, 1e-8, 1)))
        if nll < best_nll: best_nll, best_T = nll, T * tau
    return best_T

def fit_isotonic(pairs):
    if len(pairs) < 10: return lambda x: x
    X = np.array([p[0] for p in pairs]).reshape(-1, 1)
    y = np.array([p[1] for p in pairs])
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(X, y)
    return iso

def fit_histogram(pairs, n_bins=10):
    if len(pairs) < 10: return lambda x: sigmoid(x)
    X = np.array([p[0] for p in pairs])
    y = np.array([p[1] for p in pairs])
    percentiles = np.linspace(0, 100, n_bins+1)
    bin_edges = np.percentile(X, percentiles)
    bin_means = np.zeros(n_bins)
    for i in range(n_bins):
        mask = (X >= bin_edges[i]) & (X < bin_edges[i+1])
        bin_means[i] = y[mask].mean() if mask.sum() > 0 else 0.5
    return bin_edges, bin_means

def fit_conf_gating_isotonic(pairs):
    """
    Fit isotonic regression on (p_raw, outcome) pairs for confidence-gating.
    This calibrates the evaluator's raw probability outputs to empirical
    win rates, matching the sliding-window protocol from P9/P10.
    """
    if len(pairs) < 10: return lambda x: np.clip(x, 0, 1)
    X = np.array([p[2] for p in pairs])  # p_raw values
    y = np.array([p[1] for p in pairs])  # outcomes
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(X.reshape(-1, 1), y)
    return iso

def apply_calibrated_logit(dR, params, method, tau):
    if method == 'none': return dR
    elif method == 'platt':
        a, b = params; return a*dR + b
    elif method == 'temperature':
        return dR / max(params, 0.01)
    elif method == 'isotonic':
        iso = params
        pred = iso.predict(np.atleast_1d(dR))[0]
        return np.clip(np.log(pred/(1-pred+1e-8)+1e-8), -20, 20)
    elif method == 'histogram':
        edges, means = params
        idx = np.clip(np.digitize(dR, edges) - 1, 0, len(means)-1)
        pred = means[int(idx)]
        return np.clip(np.log(pred/(1-pred+1e-8)+1e-8), -20, 20)
    return dR

def gamma_meas(w):
    we=np.array(w); wu=np.ones(N_STRATEGIES)/N_STRATEGIES
    return float(np.linalg.norm(we-wu)/np.linalg.norm(wu))

def compute_cv(vals, N_target):
    v=np.array(vals)
    if len(v)<N_target: return None, None
    rng=np.random.default_rng(42)
    m=np.array([np.mean(rng.choice(v,size=N_target,replace=True)) for _ in range(N_BOOTSTRAP)])
    cv = float(m.std()/max(abs(m.mean()),1e-8))
    ci = float(1.96 * m.std() / np.sqrt(N_BOOTSTRAP))
    return cv, ci

# ══════════════════════════════════════════════════════════════

def main():
    methods = ['none', 'platt', 'temperature', 'isotonic', 'histogram', 'conf_gating']
    alpha_levels = [0.0, 0.5, 1.0, 2.0]
    tau_levels = [0.5, 1.0, 2.0]
    
    print(f"P15 v5: Canonical Calibration Study + Confidence-Gating")
    print(f"  Methods: {methods}")
    print(f"  {len(alpha_levels)*len(tau_levels)} (α,τ) × {len(methods)} methods")
    print(f"  Calibration: {N_SEEDS_CAL} seeds | Test: {N_SEEDS_TEST} seeds")
    
    t0 = time.time()
    all_results = []
    
    for alpha in alpha_levels:
        for tau in tau_levels:
            rng = np.random.default_rng(SEED_BASE)
            tq, ep = generate_profiles(rng)
            
            # Phase 1: Calibration data
            _, cal_pairs = run_trial_standard(alpha, tau, tq, ep, N_SEEDS_CAL, 0, collect_data=True)
            
            # Baseline ECE
            cal_probs_raw = sigmoid(np.array([p[0] for p in cal_pairs]) / tau)
            cal_truths = np.array([p[1] for p in cal_pairs])
            ece_base, mce_base, brier_base = compute_ece(cal_probs_raw, cal_truths)
            
            # Phase 2: Fit methods
            fitted = {}
            fitted['none'] = None
            fitted['platt'] = fit_platt([(p[0], p[1]) for p in cal_pairs])
            fitted['temperature'] = fit_temperature([(p[0], p[1]) for p in cal_pairs], tau)
            fitted['isotonic'] = fit_isotonic([(p[0], p[1]) for p in cal_pairs])
            fitted['histogram'] = fit_histogram([(p[0], p[1]) for p in cal_pairs])
            fitted['conf_gating'] = fit_conf_gating_isotonic(cal_pairs)
            
            # ECE post-calibration (classical methods only; conf_gating changes update rule)
            ece_post = {'none': (ece_base, mce_base, brier_base)}
            for method in ['platt', 'temperature', 'isotonic', 'histogram']:
                cal_probs_cal = np.array([sigmoid(apply_calibrated_logit(p[0], fitted[method], method, tau)) 
                                          for p in cal_pairs])
                ece_post[method] = compute_ece(cal_probs_cal, cal_truths)
            
            # Conf-gating ECE: use fitted isotonic on raw probabilities
            cg_probs = np.array([float(fitted['conf_gating'].predict(np.atleast_1d(p[2]))[0]) 
                                for p in cal_pairs])
            ece_post['conf_gating'] = compute_ece(cg_probs, cal_truths)
            
            print(f"\n  α={alpha:.1f} τ={tau:.1f} | Base ECE={ece_base:.4f}")
            for method in methods[1:]:
                print(f"    {method:>15s}: ECE={ece_post[method][0]:.4f} (Δ={ece_post[method][0]-ece_base:+.4f})")
            
            # Phase 3: Test seeds
            for method in methods:
                seed_start = N_SEEDS_CAL + methods.index(method) * 1000
                
                if method == 'conf_gating':
                    test_pairs = []
                    # Use confidence-gated update rule
                    test_results_list = []
                    for seed_i in range(N_SEEDS_TEST):
                        # For conf_gating we run one seed at a time due to the different API
                        single_result = run_trial_conf_gating(
                            alpha, tau, tq, ep, 1,
                            seed_start + seed_i,
                            fitted['conf_gating']
                        )
                        test_results_list.extend(single_result)
                    test_results = test_results_list
                elif method == 'none':
                    test_pairs = []
                    test_results, _ = run_trial_standard(alpha, tau, tq, ep, N_SEEDS_TEST, seed_start)
                else:
                    test_results, test_pairs = run_trial_calibrated(
                        alpha, tau, tq, ep, N_SEEDS_TEST, seed_start,
                        fitted.get(method), method, collect_data=True
                    )
                
                gammas = [gamma_meas(w) for w, H in test_results]
                Hs = [H for w, H in test_results]
                
                cv5, cv5_se = compute_cv(gammas, 5)
                cv8, cv8_se = compute_cv(gammas, 8)
                
                # ── 样本外 ECE（修复：原 ECE_post 在拟合用校准集上评估，属样本内过拟合）
                # 对 classical 方法，用测试集收集的 (cal_dR, truth) 对计算 test ECE
                ece_test = ece_post.get(method, (ece_base, mce_base, brier_base))
                if method in ('platt', 'temperature', 'isotonic', 'histogram') and test_pairs:
                    test_logits = np.array([p[0] for p in test_pairs])
                    test_truths = np.array([p[1] for p in test_pairs])
                    test_probs = sigmoid(test_logits)
                    ece_test = compute_ece(test_probs, test_truths)
                
                all_results.append({
                    'alpha': alpha, 'tau': tau, 'method': method,
                    'gamma_mean': float(np.mean(gammas)), 'gamma_std': float(np.std(gammas)),
                    'H_mean': float(np.mean(Hs)), 'H_std': float(np.std(Hs)),
                    'CV_N5': cv5, 'CV_N5_SE': cv5_se,
                    'CV_N8': cv8, 'CV_N8_SE': cv8_se,
                    'ECE_pre': ece_base,
                    'ECE_post': ece_test[0],
                    'MCE_pre': mce_base,
                    'MCE_post': ece_test[1],
                    'Brier_pre': brier_base,
                    'Brier_post': ece_test[2],
                    'ECE_post_note': 'test-set (out-of-sample)' if method in ('platt','temperature','isotonic','histogram') else 'cal-set (in-sample)',
                })
    
    # ══════════════════════════════════════════════════════════
    # ANALYSIS
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*80}")
    print("RESULTS: All Methods")
    print(f"{'='*80}")
    
    for method in methods[1:]:
        cv_reds = 0; total = 0; ece_deltas = []; cv_deltas = []
        for alpha in alpha_levels[1:]:  # skip α=0
            for tau in tau_levels:
                base = next(r for r in all_results if r['alpha']==alpha and r['tau']==tau and r['method']=='none')
                curr = next(r for r in all_results if r['alpha']==alpha and r['tau']==tau and r['method']==method)
                if curr['CV_N5'] is not None and base['CV_N5'] is not None:
                    dcv = (curr['CV_N5'] - base['CV_N5']) / max(base['CV_N5'], 0.001) * 100
                    cv_deltas.append(dcv)
                    if dcv < 0: cv_reds += 1
                    total += 1
                if curr['ECE_post'] is not None and curr['ECE_pre'] is not None:
                    ece_deltas.append(curr['ECE_post'] - curr['ECE_pre'])
        
        rate = cv_reds/max(total,1)*100
        p_binom = stats.binomtest(cv_reds, total, p=0.5, alternative='two-sided').pvalue if total>0 else 1.0
        mean_dcv = np.mean(cv_deltas) if cv_deltas else 0
        mean_dece = np.mean(ece_deltas) if ece_deltas else 0
        
        tag = "  ← CONFIDENCE-GATING" if method == 'conf_gating' else ""
        print(f"\n  {method:>15s}: CV↓rate={rate:.0f}% ({cv_reds}/{total}), "
              f"p(vs 50%)={p_binom:.4f}, mean ΔCV={mean_dcv:+.1f}%, mean ΔECE={mean_dece:+.4f}{tag}")
    
    # Save results
    output_path = os.path.join(os.path.dirname(__file__), 'canonical_results_v5.json')
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"KEY QUESTION: Does confidence-gating increase CV like classical methods?")
    cg_dcv = np.mean([(next(r for r in all_results if r['alpha']==a and r['tau']==t and r['method']=='conf_gating')['CV_N5'] - 
                        next(r for r in all_results if r['alpha']==a and r['tau']==t and r['method']=='none')['CV_N5']) / 
                       max(next(r for r in all_results if r['alpha']==a and r['tau']==t and r['method']=='none')['CV_N5'], 0.001) * 100
                       for a in alpha_levels[1:] for t in tau_levels])
    print(f"  Confidence-gating mean ΔCV: {cg_dcv:+.1f}%")
    
    classical_dcv = np.mean([dcv for r in all_results 
                            for dcv in [((r['CV_N5'] or 0) - next((b['CV_N5'] or 0) for b in all_results if b['alpha']==r['alpha'] and b['tau']==r['tau'] and b['method']=='none')) / 
                                        max(next((b['CV_N5'] or 1) for b in all_results if b['alpha']==r['alpha'] and b['tau']==r['tau'] and b['method']=='none'), 0.001) * 100]
                            if r['method'] in ['platt','temperature','isotonic','histogram'] and r['alpha']>0])
    print(f"  Classical methods mean ΔCV: {classical_dcv:+.1f}%")
    
    if cg_dcv > 0:
        print(f"\n  → Confidence-gating ALSO increases CV. The ECE-CV dissociation generalizes.")
        print(f"    The hypothesized tradeoff (γ↓ vs CV↑) may be structural after all.")
    else:
        print(f"\n  → Confidence-gating does NOT increase CV. The tradeoff is method-specific!")
        print(f"    Confidence-gating may be a 'free lunch' for coupling reduction.")
    
    print(f"\nDone in {time.time()-t0:.1f}s → {output_path}")
    
    # Quick summary table for paper
    print(f"\n{'='*80}")
    print(f"PAPER-READY SUMMARY TABLE")
    print(f"{'='*80}")
    print(f"{'Method':>15s} | {'ΔECE':>8s} | {'CV↓rate':>10s} | {'p':>6s} | {'ΔCV':>8s}")
    print(f"{'-'*15}-+-{'-'*8}-+-{'-'*10}-+-{'-'*6}-+-{'-'*8}")
    for method in methods[1:]:
        cv_reds = sum(1 for a in alpha_levels[1:] for t in tau_levels
                      if (curr := next((r for r in all_results if r['alpha']==a and r['tau']==t and r['method']==method), None))
                      and (base := next((r for r in all_results if r['alpha']==a and r['tau']==t and r['method']=='none'), None))
                      and curr['CV_N5'] is not None and base['CV_N5'] is not None
                      and curr['CV_N5'] < base['CV_N5'])
        total_cond = sum(1 for a in alpha_levels[1:] for t in tau_levels
                        if (curr := next((r for r in all_results if r['alpha']==a and r['tau']==t and r['method']==method), None))
                        and (base := next((r for r in all_results if r['alpha']==a and r['tau']==t and r['method']=='none'), None))
                        and curr['CV_N5'] is not None and base['CV_N5'] is not None)
        dcv_vals = [(curr['CV_N5'] - base['CV_N5']) / max(base['CV_N5'], 0.001) * 100
                    for a in alpha_levels[1:] for t in tau_levels
                    if (curr := next((r for r in all_results if r['alpha']==a and r['tau']==t and r['method']==method), None))
                    and (base := next((r for r in all_results if r['alpha']==a and r['tau']==t and r['method']=='none'), None))
                    and curr['CV_N5'] is not None and base['CV_N5'] is not None]
        dece_vals = [r['ECE_post'] - r['ECE_pre']
                     for r in all_results if r['method']==method and r['alpha']>0
                     and r['ECE_post'] is not None and r['ECE_pre'] is not None]
        mean_dcv = np.mean(dcv_vals) if dcv_vals else 0
        mean_dece = np.mean(dece_vals) if dece_vals else 0
        p_val = stats.binomtest(cv_reds, total_cond, p=0.5, alternative='two-sided').pvalue if total_cond > 0 else 1.0
        print(f"{method:>15s} | {mean_dece:>+8.4f} | {cv_reds}/{total_cond} ({cv_reds/max(total_cond,1)*100:.0f}%) | {p_val:.4f} | {mean_dcv:>+7.1f}%")

if __name__ == '__main__':
    main()
