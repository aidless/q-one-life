# REVIEW CARD — closing_landscape（2026-09-04）

## 题目
Closing the Calibration Landscape: A Multi-Evaluator Ensemble That Reduces Coupling Without Increasing N

## 裁决：3/10（Reject——数据互斥）
- A 证据 3：表1 内部矛盾（CG γ=0.719 > Standard 0.143，与"CG 降耦合 39%"前提相反）；"Real API 0.000/1.000"把 H=1 误填 γ_V→T 列。
- B 兴趣 3；C 清晰 4。
- D：重算 evidence/cg_tee_final_results.json（15 seed real-run）：Standard γ≈0.991、CG≈0.602、CG+TEE≈0.644——**三套数字互斥**（表1 0.143/0.719/0.574 vs 重算 vs 正文"γ=0"）。

## Critical
1. 数据互斥（表1/重算/正文三套 γ 不一致）。
2. 表1 H=1 误填 γ 列。

## TODO
统一 γ 来源；透明负结果有价值但需先立正源。

## 备注
透明负结果有潜力，但当前无实证结论——重算定正源后再定去留。