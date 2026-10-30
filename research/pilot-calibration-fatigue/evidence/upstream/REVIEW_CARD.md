# REVIEW CARD — CALIBRATION_MERGED（2026-09-04）

## 题目
Calibration Fatigue, Self-Evaluation Fragility, and the Coupling-Noise Tradeoff in Multi-Agent LLM Systems

## 裁决：7/10（B+）→ **本族可信度最高的正源稿**（hedged 版本）
- A 证据 7：Reproduction 披露最诚实（v4-flash 失败、qwen32b 反转全写进正文）；核心数字可回溯 evidence/；qwen32b 240/240 run 全存档。
- B 兴趣 7：8 条件分解+2×2 联合实验+理论 bound，结构完整。
- C 清晰 7。
- D：90.8% 主 headline 仅 GPT-4o 支撑且 per-rep 未存档——高风险声明（靠 qwen32b 反转 self-correct）。

## Major
1. 图注引用 C1a/C1c/C2a 与表格 C1/C1b/C3b 命名不符（旧稿残留）。
2. 90.8% 由未存档 GPT-4o 数据得出。

## 重算（subagent）
qwen32b per-rep：pure_T=−0.004(p=.87)、pure_sync=+0.082(p=.0017)、total=+0.078(p=.0027)——反转属实。

## TODO
①90.8% 降格 GPT-4o-specific ②统一 C1a/C1b 命名 ③补 GPT-4o per-rep 存档 ④删图注残留。

## 冲突判定
90.8%/0.207/0.228 **自承正源**，UNIFIED/contagion/EFFECTS 均搬运自它；信 hedged 版本，不信 raw 数字。