# REVIEW CARD — tmlr_p9（2026-09-04）

## 题目
Calibrating the Evaluator: Does Probability Calibration Mitigate Preference Coupling in LLM Agent Feedback Loops?

## 裁决：3/8（D 否决）→ 补 raw 前不投
- A 证据 2：目录无任何结果 raw（仅 protocol 代码）；N=5 无 per-seed/CI。
- B 兴趣 5：缓解 coupling 有实用价值，但撑不起 "first study"。
- C 清晰 4：结构清晰，但文件头 "DEPRECATED 不独立投；供主稿引用" 却打 submission.zip——自相矛盾。
- D 否决成立：规划注泄漏 + 引用错标 + 疑似拷贝。

## Critical / Major
1. **Control2 拷贝嫌疑**：校准后 0.744/0.806 在主表三处位置完全相同（L144-147 vs L158）——疑似复制粘贴。
2. **引用错标**："embedding 空间校准层级反转"归因 grinsztajn2022tree（L38, L57），实为自家 p6 未发表发现。
3. **与同族重叠未披露**："first study" 与 CALIBRATION_UNIFIED（γ↓35-37%/42%）重叠得厉害。
- Major：规模声称 ~2,400 rounds→3,600+2,400 调用（3,600 无来源）；"calibration"实为 confidence gating，未报告 evaluator ECE；31% 与 0.58±0.14/0.64±0.12 无 raw。

## TODO
1. 发 4 条件 per-seed raw + CI 自证 0.744/0.806（或删 Control2 重复行）。
2. 删 DEPRECATED 头注；修 grinsztajn 引用归回 p6。
3. 补 evaluator ECE/校准曲线；解释调用口径与同族重叠。
4. "first study" 降格。

## 备注
与 CALIBRATION_UNIFIED 等重叠度高——建议并入校准族正典而非独立投。