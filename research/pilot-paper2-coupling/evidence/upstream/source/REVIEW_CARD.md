# REVIEW CARD — PAPER2_CONSOLIDATED（2026-09-04）

## 题目
A Conditional Coupling–Diversity–Precision Bound for TTRL-based…（族稿）

## 裁决：3/8（D 否决——模板串稿+占位；清洁后可 5-6）→ 重写声明后再投
- A 证据 6：r=−0.9977、乘积 0.080、15.4×、CNR 2.94/6.3、√5 全部验算通过；条件化框架（CR 下界非 tight、logit 估计器 10/21 越界）诚实。
- B 兴趣 5：窄而有诚意的条件化负面结果。
- C 清晰 3：三连重复 Reproducibility + L432 占位 URL + 标题已是 Conditional 但正文多处 "impossibility triangle" + 内部代号 "PAPER4" 泄漏。
- D 否决成立：双份 "Novelty positioning" 讲的是 calibration fatigue（本文不研究 → 家族模板串稿）；L44 Contributions 占位措辞（"the target phenomenon"）。

## Major
- M1 三连重复结构（L526/533/540）+ 占位 URL。
- M2 串稿 novelty/contributions 块（主题错位）。
- M3 复现协议与实验不匹配：模板说 OPENAI_API_KEY + run_all_experiments.py 在线复跑，本文实为 3GB 历史日志**离线重建**（L33/L439 "available from the authors upon request"）——该块 ≥8 篇家族稿逐字出现。
- M4 版本残留：impossibility-triangle 表述、PAPER4 代号、模型名 V4-Pro vs V3。
- M5 跨篇数值不一致：convergence half-life 14–19/r=0.76/p=0.13 vs PAPER13 15–19/r=0.83/p=0.08；Arena CI 两稿不同。
- 重算通过：r=−0.9977（Table1 五行手算✓）、全部乘积✓、2.42/0.157=15.4✓、γ=1→N≈57(45-96 内)✓。

## TODO
1. 删三连重复段 + 替换 L432 占位 URL。
2. 删 L40/L75/L44 串稿块，写本文真实贡献。
3. 复现协议改离线重建+归档清单；修 V3/V4-Pro、去 impossibility-triangle 与 PAPER4 代号。
4. 与 PAPER13 对齐共享数值并声明去重。

## 备注
理论核可复核，但被家族模板淹没；与 PAPER13 共享数值不一致需先和解。