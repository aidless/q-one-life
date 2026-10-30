"""Single-source regeneration of T30 joint artifacts (2026-09-10).

Canonical source: the 120 per-seed JSONs [ABCD]_seed*.json in
evidence/f9_uniform_T30_results/. Regenerates all_results.csv and
analysis_summary.json deterministically.

Recovered conventions (calibrated on condition A, which had zero drift):
- acc = mean of per-agent correctness means (= flat mean on this data)
- gamma_final = per_round[-1]['gamma']  (exact on all matching seeds)
- std = population SD (numpy ddof=0)     (exact)
- main-effect p = Student's two-sample t-test, scipy.stats.ttest_ind default (exact)
- main-effect d = mean diff / pooled SD with ddof=0                     (exact)
- interaction effect = (D-C) - (B-A) on condition means                 (exact)
- interaction p: ORIGINAL METHOD UNRECOVERABLE (no standard test on the
  prior data reproduces the old pins). Recomputed via standard 2x2 ANOVA
  F-test (F = (n*L^2/4)/MSE, df=(1,116)). All four metrics remain ns,
  so no conclusion changes. Documented as an explicit method change.
"""
import json, csv, glob, os
import numpy as np
from scipy import stats

D = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 'f9_uniform_T30_results')

def flat(x):
    for v in x:
        if isinstance(v, list):
            yield from flat(v)
        elif isinstance(v, (int, float)):
            yield v

def acc_of(d):
    c = d['per_agent_correctness']
    return float(np.mean([np.mean(list(flat(a))) for a in c]))

files = sorted(glob.glob(os.path.join(D, '[ABCD]_seed*.json')))
assert len(files) == 120, len(files)
recs = []
for f in files:
    d = json.load(open(f))
    recs.append({
        'condition': d['condition'], 'seed': int(d['seed']),
        'comm_on': bool(d['comm_on']), 'cal_on': bool(d['cal_on']),
        'ECE': float(d['ECE']), 'gamma_mean': float(d['gamma_mean']),
        'gamma_final': float(d['per_round'][-1]['gamma']),
        'H_final': float(d['H_final']), 'acc': acc_of(d),
        'elapsed_sec': float(d['elapsed_sec']),
    })
recs.sort(key=lambda r: (r['condition'], r['seed']))

COLS = ['condition', 'seed', 'comm_on', 'cal_on', 'ECE', 'gamma_mean',
        'gamma_final', 'H_final', 'acc', 'elapsed_sec']
with open(os.path.join(D, 'all_results.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    for r in recs:
        w.writerow({k: repr(r[k]) if isinstance(r[k], float) else r[k]
                    for k in COLS})

by = {}
for c in 'ABCD':
    by[c] = [r for r in recs if r['condition'] == c]
    assert len(by[c]) == 30, (c, len(by[c]))

def mean(a):
    return float(np.mean(a))

def sd0(a):
    return float(np.std(a, ddof=0))

conditions = {}
for c in 'ABCD':
    rr = by[c]
    conditions[c] = {
        'n': 30,
        'ECE_mean': mean([r['ECE'] for r in rr]),
        'ECE_std': sd0([r['ECE'] for r in rr]),
        'gamma_mean': mean([r['gamma_mean'] for r in rr]),
        'gamma_std': sd0([r['gamma_mean'] for r in rr]),
        'H_mean': mean([r['H_final'] for r in rr]),
        'H_std': sd0([r['H_final'] for r in rr]),
        'acc_mean': mean([r['acc'] for r in rr]),
        'acc_std': sd0([r['acc'] for r in rr]),
    }

def pooled_sd0(a, b):
    return float(np.sqrt((np.var(a, ddof=0) + np.var(b, ddof=0)) / 2))

def main_effect(on, off):
    on = np.asarray(on, dtype=float)
    off = np.asarray(off, dtype=float)
    t, p = stats.ttest_ind(on, off)
    return float(on.mean() - off.mean()), float(p), \
        float((on.mean() - off.mean()) / pooled_sd0(on, off))

def anova_block(vals):
    v = {c: np.array([r[vals] for r in by[c]], dtype=float) for c in 'ABCD'}
    comm_on = np.concatenate([v['B'], v['D']])
    comm_off = np.concatenate([v['A'], v['C']])
    cal_on = np.concatenate([v['C'], v['D']])
    cal_off = np.concatenate([v['A'], v['B']])
    ce, pc, dc = main_effect(comm_on, comm_off)
    ke, pk, dk = main_effect(cal_on, cal_off)
    m = {c: float(v[c].mean()) for c in 'ABCD'}
    L = (m['D'] - m['C']) - (m['B'] - m['A'])
    mse = float(np.mean([v[c].var(ddof=1) for c in 'ABCD']))
    F = (30 * L ** 2 / 4) / mse
    pint = float(stats.f.sf(F, 1, 116))
    return {'comm_effect': ce, 'p_comm': pc, 'd_comm': dc,
            'cal_effect': ke, 'p_cal': pk, 'd_cal': dk,
            'interaction': L, 'p_interaction': pint, 'means': m}

summary = {
    'total_seeds': 120,
    'conditions': conditions,
    'anova': {'ECE': anova_block('ECE'),
              'gamma_mean': anova_block('gamma_mean'),
              'H_final': anova_block('H_final'),
              'acc': anova_block('acc')},
}
with open(os.path.join(D, 'analysis_summary.json'), 'w') as f:
    json.dump(summary, f, indent=2)

print('B ECE/gamma: %.6f %.6f' % (conditions['B']['ECE_mean'],
                                  conditions['B']['gamma_mean']))
print('anova ECE p:', summary['anova']['ECE']['p_comm'],
      summary['anova']['ECE']['p_cal'],
      summary['anova']['ECE']['p_interaction'])
print('OK: regenerated from 120 per-seed JSONs')
