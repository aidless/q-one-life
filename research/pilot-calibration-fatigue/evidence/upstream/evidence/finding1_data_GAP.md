# Finding-1 八条件 per-seed ECE 数据缺口（作者侧需补）

依据 R33 补充规格（REVIEW_R33_4POINT_SUPPLEMENT_SPEC.md）补充项 1。

## 缺失内容
The requested eight-condition per-repetition artifact (not delivered in this package):
- 8 个条件（C1/Q5/C3b/C3/Q2/C1b/C2/C4），每条件 **30 个独立重复**的 `final_ECE_per_rep`（30 个 float）；
- 种子规范：30 reps 种子已记录；bootstrap B=5000、seed 42。

## 期望均值（用于校验，来自正文表）
C1=0.012、Q5=0.035、C3b=0.017、C3=0.018、Q2=0.208、C1b=0.219、C2=0.241、C4=0.234
（各含 95% CI，见 verify_finding1.py 中的 EXPECTED 表）。

## 本地现状
- 仅有 `analyses/p1a_pilot_*`（每条件 2 reps 的退化试点，final_ece 恒 0.05，不可用作真实数据）；
- 完整 30-rep 实验（GPT-4o × GSM8K × 8 条件）的 per-rep 输出不在本机可访问路径；
- 交付 `verify_finding1.py`：数据文件就位后运行即输出验证 JSON 并逐项比对（容差 1e-3）。

## 需要作者提供
1. 8 条件 × 30 的 final ECE per-rep 数组（JSON，schema 见规格书）；
2. 或原始实验日志（per-rep records），由作者侧脚本聚合为 final ECE。

## 提供后自动动作
1. 运行 `python evidence/scripts/verify_finding1.py` → 生成 finding1_verification_20260810.json；
2. 两包 manifest 同步；evidence_ref_check 全 PASS；
3. 该数据补齐后 CAL S 3.8→4.0 的唯一本地缺口关闭。
## 更新（2026-08-10 深搜后）
- 全盘搜索确认：完整 30-rep 数据不在本机（详见 FINDING1_DATA_SEARCH_VERDICT.md）。
- **p1a_pilot 复现实验失败**（p1a_pilot_summary_20260808.json：易题 acc=conf=1.0、ECE≈0.05，protocol comparability NOT established）——论文 Finding-1 数字源自 P3 时代实验，原始 per-rep 输出未随包交付。
- 选项：作者提供原始数据（首选）/ 重跑（按 pilot 建议改难题+过度自信注入）/ 降级声明。
