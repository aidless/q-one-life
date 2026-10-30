#!/usr/bin/env python3
"""Analyze P35 chain extension results: compute BDS (length-based proxy)
between single and chain_final for each model across M-011..M-020."""
import json, os, numpy as np
from collections import defaultdict

# The study host's path was a Windows absolute path, so the delivered copy
# could not run anywhere else. Resolve the results directory from this file's
# own location, falling back to the original so the record of where it ran
# survives.
_d = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  'results', 'cloud_chain_ext')
d = _d if os.path.isdir(_d) else r"F:\Research\PAPER35_FRONT_DRIFT\experiments\multi_agent\results\cloud_chain_ext"
data = defaultdict(list)

for f in sorted(os.listdir(d)):
    if not f.endswith('.jsonl'):
        continue
    model = f.split('__')[0]
    for line in open(os.path.join(d, f), encoding='utf-8'):
        r = json.loads(line)
        single = r.get('single', '')
        chain = r.get('chain', [])
        final = chain[-1] if chain else ''
        # BDS proxy: normalized length difference (simpler than token-level)
        sl = len(single)
        fl = len(final)
        bds = abs(sl - fl) / max(sl, fl, 1) if max(sl, fl) > 0 else 0
        data[model].append({
            'scenario_id': r['scenario_id'],
            'single_len': sl,
            'chain_final_len': fl,
            'bds_proxy': bds,
            'chain_grew': fl > sl
        })

print("model | n | single_mean | chain_final_mean | bds_proxy_mean | grew_rate")
results = {}
for model in sorted(data):
    rows = data[model]
    sl = np.mean([r['single_len'] for r in rows])
    fl = np.mean([r['chain_final_len'] for r in rows])
    bds = np.mean([r['bds_proxy'] for r in rows])
    grew = np.mean([1 if r['chain_grew'] else 0 for r in rows])
    results[model] = {'n': len(rows), 'single_mean': sl, 'chain_mean': fl, 'bds': bds, 'grew': grew}
    print(f"{model:20s} | {len(rows):3d} | {sl:11.1f} | {fl:16.1f} | {bds:.4f} | {grew:.2f}")

# Save as JSON
with open(os.path.join(d, 'chain_ext_analysis.json'), 'w') as f:
    json.dump(results, f, indent=2)
print("\nSaved chain_ext_analysis.json")
