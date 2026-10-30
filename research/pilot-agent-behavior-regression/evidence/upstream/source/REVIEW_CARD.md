# REVIEW CARD — PAPER35_FRONT_DRIFT（2026-09-04）

## 题目
Agent Behavior Regression Testing for Local LLM Systems: Setting a Front-End Baseline

## 裁决：4/10（D 否决——前端漂移）→ 清前端前不可投
- A 证据 5：BDS 种子-模型二象性选题真实但呈现自相矛盾。
- B 兴趣 4：前端整体漂移使全文不可信。
- C 清晰 4：正文清晰但前端（L75 Novelty/L79 Contributions/L79-90 Setup/L652+L659 双 Reproducibility）
  全是 calibration 族样板——GPT-4o/GSM8K/ECE/γ/H/CV/run_all_experiments.py，与本文本地 Ollama 100 场景 BDS 完全不匹配。
- D 否决成立：L309 "no API calls" vs L505/L513 cloud 矛盾；L58 "prove BDS consistent" vs L283 自认仅 heuristic（overclaim）。

## Critical / Major
1. 前端漂移（审稿人无法判断哪个实验为真）。
2. L309 vs L505/L513 无 API 矛盾。
3. L652 与 L659 重复 Reproducibility 段。
4. Theorem 1 overclaim（L58 vs L283）。

## TODO
删前端漂移段 → 统一 Reproducibility → 修 Theorem 1 表述 → 补 BDS 复算 CLI。

## 备注
compliance 是主题词（length-compliance 类别，非审计泄漏）；清漂移后可救。