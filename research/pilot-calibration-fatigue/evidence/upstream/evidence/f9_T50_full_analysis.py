#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F9 T=50 完整分析脚本
等 T=50 实验完成后直接运行：python f9_T50_full_analysis.py

分析内容：
1. 基础 2x2 ANOVA（整体效应，T=50 vs T=30）
2. 早期 vs 晚期对比（R1-5 vs R46-50，验证 Comm 效应是否增强）
3. per-round 效应量趋势（R1-R50，Comm 和 Cal 的 d 值随时间变化）
4. T=30 vs T=50 对比（相同 round 范围的效应量对比）
5. 机制分析（收敛速度、agent 异质性 JSD、策略分布均匀性）
6. 生成 analysis_summary.json + deep_analysis.json + mechanism_analysis.json
"""
import json
import os
import sys
import numpy as np
from scipy import stats
from pathlib import Path
from datetime import datetime

# ============ 配置 ============
T50_DIR = "/data3/Research/CALIBRATION_MERGED/evidence/f9_t50_results"
T30_DIR = "/data3/Research/CALIBRATION_MERGED/evidence/f9_uniform_T30_results"
OUTPUT_DIR = "/data3/Research/CALIBRATION_MERGED/evidence/f9_T50_analysis"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CONDITIONS = ['A', 'B', 'C', 'D']
N_SEEDS = 30
T_MAX = 50

# ============ 工具函数 ============
def load_seed_data(cond, seed_idx, base_dir=T50_DIR):
    """加载单个 seed 的数据"""
    fname = os.path.join(base_dir, f"{cond}_seed{seed_idx:03d}.json")
    if not os.path.exists(fname):
        return None
    with open(fname, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_all_data(base_dir=T50_DIR):
    """加载所有条件所有 seed 的数据"""
    data = {c: [] for c in CONDITIONS}
    for cond in CONDITIONS:
        for seed in range(N_SEEDS):
            d = load_seed_data(cond, seed, base_dir)
            if d is not None:
                data[cond].append(d)
    return data

def cohens_d(a, b):
    """Cohen's d（合并标准差）"""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 0.0
    s1, s2 = np.std(a, ddof=1), np.std(b, ddof=1)
    pooled = np.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
    return (np.mean(a) - np.mean(b)) / pooled if pooled > 0 else 0.0

def get_metric_at_round(data_list, metric, round_idx):
    """获取一组 seed 在指定 round 的指标值"""
    values = []
    for d in data_list:
        rounds = d.get('per_round', [])
        if round_idx < len(rounds):
            values.append(rounds[round_idx].get(metric, np.nan))
    return np.array(values)

def get_final_metric(data_list, metric):
    """获取最终 round 的指标值"""
    return get_metric_at_round(data_list, metric, -1)

# ============ 分析 1: 基础 2x2 ANOVA ============
def analysis_overall(data):
    """整体 2x2 分析（最终 round）"""
    print("\n" + "="*70)
    print("[1] 整体 2x2 分析（最终 round, T=50）")
    print("="*70)
    
    results = {}
    metrics = ['gamma', 'H', 'ECE', 'accuracy']
    
    for metric in metrics:
        print(f"\n  指标: {metric}")
        A = get_final_metric(data['A'], metric)
        B = get_final_metric(data['B'], metric)
        C = get_final_metric(data['C'], metric)
        D = get_final_metric(data['D'], metric)
        
        # 描述统计
        for name, arr in [('A', A), ('B', B), ('C', C), ('D', D)]:
            if len(arr) > 0:
                print(f"    {name}: n={len(arr)}, mean={np.mean(arr):.4f}, sd={np.std(arr, ddof=1):.4f}")
        
        # Comm 主效应: (B+D) vs (A+C)
        comm_on = np.concatenate([B, D])
        comm_off = np.concatenate([A, C])
        t_comm, p_comm = stats.ttest_ind(comm_on, comm_off, equal_var=False)
        d_comm = cohens_d(comm_on, comm_off)
        print(f"    Comm: t={t_comm:.3f}, p={p_comm:.4f}, d={d_comm:.3f}")
        
        # Cal 主效应: (C+D) vs (A+B)
        cal_on = np.concatenate([C, D])
        cal_off = np.concatenate([A, B])
        t_cal, p_cal = stats.ttest_ind(cal_on, cal_off, equal_var=False)
        d_cal = cohens_d(cal_on, cal_off)
        print(f"    Cal:  t={t_cal:.3f}, p={p_cal:.4f}, d={d_cal:.3f}")
        
        # 交互: (D-C) vs (B-A)
        int_cal = D - C if len(D) == len(C) else np.array([])
        int_nocal = B - A if len(B) == len(A) else np.array([])
        if len(int_cal) > 1 and len(int_nocal) > 1:
            t_int, p_int = stats.ttest_ind(int_cal, int_nocal, equal_var=False)
            d_int = cohens_d(int_cal, int_nocal)
            print(f"    Comm×Cal: t={t_int:.3f}, p={p_int:.4f}, d={d_int:.3f}")
        
        results[metric] = {
            'comm': {'t': float(t_comm), 'p': float(p_comm), 'd': float(d_comm)},
            'cal': {'t': float(t_cal), 'p': float(p_cal), 'd': float(d_cal)},
            'means': {c: float(np.mean(get_final_metric(data[c], metric))) for c in CONDITIONS if len(get_final_metric(data[c], metric)) > 0}
        }
    
    return results

# ============ 分析 2: 早期 vs 晚期对比 ============
def analysis_early_vs_late(data):
    """早期（R1-5）vs 晚期（R46-50）对比"""
    print("\n" + "="*70)
    print("[2] 早期 vs 晚期对比（R1-5 vs R46-50）")
    print("="*70)
    
    results = {}
    metrics = ['gamma', 'H']
    
    for metric in metrics:
        print(f"\n  指标: {metric}")
        
        for phase_name, rounds in [('early_R1-5', range(0, 5)), ('late_R46-50', range(45, 50))]:
            # 每个 seed 取该阶段的均值
            def phase_means(cond_data):
                vals = []
                for d in cond_data:
                    round_vals = []
                    for r in rounds:
                        if r < len(d.get('per_round', [])):
                            round_vals.append(d['per_round'][r].get(metric, np.nan))
                    if round_vals:
                        vals.append(np.nanmean(round_vals))
                return np.array(vals)
            
            A = phase_means(data['A'])
            B = phase_means(data['B'])
            C = phase_means(data['C'])
            D = phase_means(data['D'])
            
            comm_on = np.concatenate([B, D])
            comm_off = np.concatenate([A, C])
            t, p = stats.ttest_ind(comm_on, comm_off, equal_var=False)
            d = cohens_d(comm_on, comm_off)
            print(f"    {phase_name}: Comm t={t:.3f}, p={p:.4f}, d={d:.3f}")
            
            if metric not in results:
                results[metric] = {}
            results[metric][phase_name] = {'t': float(t), 'p': float(p), 'd': float(d)}
    
    return results

# ============ 分析 3: per-round 效应量趋势 ============
def analysis_per_round_trend(data):
    """per-round Comm 和 Cal 效应量趋势（R1-R50）"""
    print("\n" + "="*70)
    print("[3] per-round 效应量趋势（R1-R50）")
    print("="*70)
    
    results = {'rounds': list(range(1, T_MAX+1)), 'comm_d': [], 'cal_d': [], 'comm_p': [], 'cal_p': []}
    
    for r in range(T_MAX):
        # Comm 效应
        comm_on = np.concatenate([
            get_metric_at_round(data['B'], 'gamma', r),
            get_metric_at_round(data['D'], 'gamma', r)
        ])
        comm_off = np.concatenate([
            get_metric_at_round(data['A'], 'gamma', r),
            get_metric_at_round(data['C'], 'gamma', r)
        ])
        comm_on = comm_on[~np.isnan(comm_on)]
        comm_off = comm_off[~np.isnan(comm_off)]
        
        if len(comm_on) > 1 and len(comm_off) > 1:
            t, p = stats.ttest_ind(comm_on, comm_off, equal_var=False)
            d = cohens_d(comm_on, comm_off)
        else:
            t, p, d = 0, 1, 0
        
        results['comm_d'].append(float(d))
        results['comm_p'].append(float(p))
        
        # Cal 效应
        cal_on = np.concatenate([
            get_metric_at_round(data['C'], 'gamma', r),
            get_metric_at_round(data['D'], 'gamma', r)
        ])
        cal_off = np.concatenate([
            get_metric_at_round(data['A'], 'gamma', r),
            get_metric_at_round(data['B'], 'gamma', r)
        ])
        cal_on = cal_on[~np.isnan(cal_on)]
        cal_off = cal_off[~np.isnan(cal_off)]
        
        if len(cal_on) > 1 and len(cal_off) > 1:
            t, p = stats.ttest_ind(cal_on, cal_off, equal_var=False)
            d = cohens_d(cal_on, cal_off)
        else:
            t, p, d = 0, 1, 0
        
        results['cal_d'].append(float(d))
        results['cal_p'].append(float(p))
    
    # 打印关键 round
    for r in [0, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49]:
        if r < len(results['comm_d']):
            print(f"  R{r+1:2d}: Comm d={results['comm_d'][r]:.3f} (p={results['comm_p'][r]:.4f}), "
                  f"Cal d={results['cal_d'][r]:.3f} (p={results['cal_p'][r]:.4f})")
    
    return results

# ============ 分析 4: T=30 vs T=50 对比 ============
def analysis_T30_vs_T50(data_t50, data_t30):
    """T=30 vs T=50 对比（相同 round 范围）"""
    print("\n" + "="*70)
    print("[4] T=30 vs T=50 对比")
    print("="*70)
    
    results = {}
    
    # 对比 R26-30 的 Comm 效应
    for metric in ['gamma', 'H']:
        print(f"\n  指标: {metric}, R26-30")
        
        for name, data in [('T=30', data_t30), ('T=50', data_t50)]:
            def phase_means(cond_data):
                vals = []
                for d in cond_data:
                    round_vals = []
                    for r in range(25, 30):
                        if r < len(d.get('per_round', [])):
                            round_vals.append(d['per_round'][r].get(metric, np.nan))
                    if round_vals:
                        vals.append(np.nanmean(round_vals))
                return np.array(vals)
            
            comm_on = np.concatenate([phase_means(data['B']), phase_means(data['D'])])
            comm_off = np.concatenate([phase_means(data['A']), phase_means(data['C'])])
            t, p = stats.ttest_ind(comm_on, comm_off, equal_var=False)
            d = cohens_d(comm_on, comm_off)
            print(f"    {name}: Comm d={d:.3f}, p={p:.4f}")
            
            if metric not in results:
                results[metric] = {}
            results[metric][name] = {'d': float(d), 'p': float(p)}
    
    return results

# ============ 分析 5: 机制分析 ============
def analysis_mechanism(data):
    """机制分析：收敛速度、agent 异质性、策略分布"""
    print("\n" + "="*70)
    print("[5] 机制分析")
    print("="*70)
    
    results = {}
    
    # 5.1 收敛速度：gamma 达到最终值 90% 所需的 round 数
    print("\n  [5.1] 收敛速度（gamma 达到 90% 最终值的 round）")
    convergence_rounds = {}
    for cond in CONDITIONS:
        rounds_list = []
        for d in data[cond]:
            rounds = d.get('per_round', [])
            if not rounds:
                continue
            final_gamma = rounds[-1].get('gamma', 0)
            if final_gamma <= 0:
                continue
            for i, r in enumerate(rounds):
                if r.get('gamma', 0) >= 0.9 * final_gamma:
                    rounds_list.append(i + 1)
                    break
        if rounds_list:
            convergence_rounds[cond] = float(np.mean(rounds_list))
            print(f"    {cond}: mean={np.mean(rounds_list):.1f} rounds, n={len(rounds_list)}")
    
    results['convergence_speed'] = convergence_rounds
    
    # Comm 对收敛速度的影响
    comm_on_conv = [convergence_rounds[c] for c in ['B', 'D'] if c in convergence_rounds]
    comm_off_conv = [convergence_rounds[c] for c in ['A', 'C'] if c in convergence_rounds]
    if comm_on_conv and comm_off_conv:
        print(f"    Comm 效应: comm_on={np.mean(comm_on_conv):.1f}, comm_off={np.mean(comm_off_conv):.1f}, "
              f"差异={np.mean(comm_on_conv)-np.mean(comm_off_conv):.1f} rounds")
        results['convergence_comm_effect'] = float(np.mean(comm_on_conv) - np.mean(comm_off_conv))
    
    # 5.2 最终 H（策略多样性）
    print("\n  [5.2] 最终 H（策略多样性）")
    for cond in CONDITIONS:
        H_vals = get_final_metric(data[cond], 'H')
        if len(H_vals) > 0:
            print(f"    {cond}: mean={np.mean(H_vals):.4f}, sd={np.std(H_vals, ddof=1):.4f}")
    
    comm_on_H = np.concatenate([get_final_metric(data['B'], 'H'), get_final_metric(data['D'], 'H')])
    comm_off_H = np.concatenate([get_final_metric(data['A'], 'H'), get_final_metric(data['C'], 'H')])
    t_H, p_H = stats.ttest_ind(comm_on_H, comm_off_H, equal_var=False)
    d_H = cohens_d(comm_on_H, comm_off_H)
    print(f"    Comm 效应: d={d_H:.3f}, p={p_H:.4f}")
    results['final_H_comm_effect'] = {'d': float(d_H), 'p': float(p_H)}
    
    return results

# ============ 主函数 ============
def main():
    print("="*70)
    print(f"F9 T=50 完整分析 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 检查数据完整性
    t50_data = load_all_data(T50_DIR)
    total = sum(len(v) for v in t50_data.values())
    print(f"\nT=50 数据: {total}/120 seeds")
    for c in CONDITIONS:
        print(f"  {c}: {len(t50_data[c])}/30")
    
    if total < 120:
        print(f"\n⚠️  数据不完整（{total}/120），分析结果可能有偏差")
        print("   建议等实验完成后重新运行")
    
    # 加载 T=30 数据（用于对比）
    t30_data = load_all_data(T30_DIR)
    total_t30 = sum(len(v) for v in t30_data.values())
    print(f"\nT=30 数据: {total_t30}/120 seeds")
    
    # 运行所有分析
    overall = analysis_overall(t50_data)
    early_late = analysis_early_vs_late(t50_data)
    per_round = analysis_per_round_trend(t50_data)
    t30_t50 = analysis_T30_vs_T50(t50_data, t30_data)
    mechanism = analysis_mechanism(t50_data)
    
    # 保存结果
    summary = {
        'timestamp': datetime.now().isoformat(),
        'n_seeds_t50': {c: len(t50_data[c]) for c in CONDITIONS},
        'n_seeds_t30': {c: len(t30_data[c]) for c in CONDITIONS},
        'overall': overall,
        'early_vs_late': early_late,
        't30_vs_t50': t30_t50,
        'mechanism': mechanism,
    }
    
    summary_path = os.path.join(OUTPUT_DIR, 'analysis_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 分析摘要已保存: {summary_path}")
    
    deep_path = os.path.join(OUTPUT_DIR, 'deep_analysis.json')
    with open(deep_path, 'w', encoding='utf-8') as f:
        json.dump({'per_round_trend': per_round}, f, indent=2, ensure_ascii=False)
    print(f"✅ 深度分析已保存: {deep_path}")
    
    mech_path = os.path.join(OUTPUT_DIR, 'mechanism_analysis.json')
    with open(mech_path, 'w', encoding='utf-8') as f:
        json.dump(mechanism, f, indent=2, ensure_ascii=False)
    print(f"✅ 机制分析已保存: {mech_path}")
    
    # 关键结论
    print("\n" + "="*70)
    print("关键结论")
    print("="*70)
    
    # 整体 Comm 效应（gamma）
    comm_overall = overall.get('gamma', {}).get('comm', {})
    print(f"\n1. 整体 Comm 效应（gamma, T=50）: d={comm_overall.get('d', 0):.3f}, p={comm_overall.get('p', 1):.4f}")
    if comm_overall.get('p', 1) < 0.05:
        print("   → 显著")
    else:
        print("   → 不显著（与 T=30 一致：收敛后无整体效应）")
    
    # 晚期 Comm 效应
    late_comm = early_late.get('gamma', {}).get('late_R46-50', {})
    print(f"\n2. 晚期 Comm 效应（gamma, R46-50）: d={late_comm.get('d', 0):.3f}, p={late_comm.get('p', 1):.4f}")
    if late_comm.get('p', 1) < 0.05:
        print("   → 显著！T=50 晚期 Comm 效应增强")
    else:
        print("   → 不显著")
    
    # T=30 vs T=50 对比
    t30_comm = t30_t50.get('gamma', {}).get('T=30', {})
    t50_comm = t30_t50.get('gamma', {}).get('T=50', {})
    print(f"\n3. R26-30 Comm 效应对比:")
    print(f"   T=30: d={t30_comm.get('d', 0):.3f}, p={t30_comm.get('p', 1):.4f}")
    print(f"   T=50: d={t50_comm.get('d', 0):.3f}, p={t50_comm.get('p', 1):.4f}")
    
    # 机制
    conv_effect = mechanism.get('convergence_comm_effect', 0)
    print(f"\n4. 机制：Comm 使收敛延迟 {conv_effect:.1f} rounds")
    H_effect = mechanism.get('final_H_comm_effect', {})
    print(f"   最终 H Comm 效应: d={H_effect.get('d', 0):.3f}, p={H_effect.get('p', 1):.4f}")
    
    print("\n" + "="*70)
    print("分析完成！")
    print("="*70)

if __name__ == "__main__":
    main()
