# REVIEW CARD — RESAMPLING_CALIBRATION（2026-09-04）

## 题目
N-Sensitive Calibration of Tree Ensembles on Frozen LLM Embeddings

## 裁决：5/10（B-）→ **并入 tmlr_p12**（方向与校准族不同：树集成 N-敏感性）
- A 证据 6：头注 DEPRECATED 并入 p12；修正 sklearn 管线 bug、补 adaptive ECE/per-N 调参，修订诚实。
- B 兴趣 5。
- C 清晰 6：类合并消融+多协议对比+50 种子。
- D：内部数字口径不统一。

## Major
1. abstract "TS 减少 RF ECE 88%" OK 但 Finding 2a 正文 "ECE 0.128–0.135" vs 表 0.131 表述不一致；"RF 优于 MLP"（N=5000 单点）与 N-敏感性"MLP 大胜 0.35"并置易误导。
2. Tab embedding_main caption 称 "across all three" 但只显示 BGE。
- Minor：主稿 Adaptive ECE vs appendix EW-ECE 数值差 1.7-1.9×，需显式提醒。

## TODO
归档至 p12；统一 ECE 口径表述。

## 冲突判定
无正典数字冲突（不与 +0.047/90.8% 争）；仅数字口径需整理。