# REVIEW CARD — MERGED_FLAGSHIPS/F2_Theory（2026-09-04）

## 题目
Merged Flagship F2: K-Generalization, Selective Prediction and Self-Evaluation

## 裁决：2/10（D 否决——中央实证数据伪造）→ 拒稿，重做实验
- A 证据 1-2：旗舰 "2700 cells 9/9 holds" 造假。
- B 兴趣 2：理论正文一段教科书 Cramér-Rao；题目与内容（drift/causal/Finance/CRM）脱节。
- C 清晰 2：规划/审计注进正文（"suggestion 11/48/56"、"G3/G4 PASS"、"this revision does not modify the proof"）、空白图占位。
- D 否决成立。

## Critical（本人重算实锤 2026-09-04）
1. **2700 伪造**：`evidence/k345/joint_2700.json` 声明 n_cells=2700、holds=2700，实际 cells 只有 6 行模板循环；
   第 3 行 (K=5, γ=2.0) 携带第 1 行 (K=3, γ=0.5) 的 product=0.4777/bound=0.0312——(K,γ)↔数值映射错乱；
   note 自认 "deterministic expansion"；Table 1 的 γ=2.0 products（0.56/0.44/0.48）在数据中不存在。
2. **144/144 与原始文件矛盾**：声称全部 holds，但 real128_combined.json 自述 "2×64=128/192, 1 batch remains"。
3. **GPU 合计错误**：表 2 宣称 4.84h，行和 1.47+1.10+0.85+0.42=3.84h。
4. **K=6 bound 矛盾**：摘要 0.014 vs 正文 0.038。
5. **跨篇串稿**：McNemar(44,11) 与 F3_Memory append-only 行逐字同值（重算 8.699e-6 ✓——同一组数出现在两篇）。

## TODO（返修）
1. 重建真实 2700 格（或把声称缩回数据实有量）——此条不解决不投。
2. 补 γ=2.0 真实数据或删 9/9 表述。
3. 核对 144/144 与 128+1 batch。
4. 修 GPU 合计与 K=6 矛盾；删除全部规划/审计注与占位图。

## 备注
与 F2_Single_10page（3.5/10，纯仿真）同一成果族，两者都不可投；若骨架（相关地板理论）有价值，
需以真实 verifier 数据重做实证，否则整个 F2 族冷冻。