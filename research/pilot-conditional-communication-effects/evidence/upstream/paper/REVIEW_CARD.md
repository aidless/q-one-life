# REVIEW CARD — PAPER13_MERGED（2026-09-04）

## 题目
Conditional Communication Effects in Multi-Agent LLM Systems: Strategy Convergence, Calibration Fatigue, and a Metric-Conditional Noise Relation

## 裁决：3/8（D 否决——家族模板串稿+内部矛盾；Rework 后可重投）→ 唯一正典候选
- A 证据 4：+0.207/90.8% 论文自认不可独立重算（L366，GPT-4o per-rep 未归档）；其自身复现（v4-flash 未复现、qwen32b 结构反转）削弱 takeaway。
- B 兴趣 5：诚实跨模型负结果值得读。
- C 清晰 3：version note 指名旧稿 + "Phase 54"×3 + extbf 缺反斜杠×2 + 双图共 label + 双份 Broader Impact/Repro + audit-set 跨稿杂块。
- D 否决成立：双份 "Novelty positioning" 且两处仍推 self-evaluation immunity（与 L105 直接矛盾）；复现协议=家族模板（L877）。

## Critical/Major（subagent 重算，行号实证）
- C1 L65/L214 CIs 重叠（[1.088,1.416] vs [1.204,1.518]）vs L675 却说 non-overlapping——自相矛盾。
- C2 摘要/贡献仍主推 GPT-4o-only "90.8% temporal first decomposition"（d=4.85），L366 自证 qwen32b 复现是**结构反转**（纯T −0.004 ns，sync +0.082 唯一显著）——takeaway 未降级。
- M3 可复现性冲突：L366 "not independently recomputable" vs L877 "bit-exact reproducibility"。
- M4 透明性回退 vs PAPER1：设计表删 seed-status caveat（+0.021 是上界）。
- M5 拼接残留：L93 双盲泄漏 + L798-801 他稿 audit-set + L111 Roadmap "Sections 8-12" 过期。
- 重算通过：0.207+0.021=0.228✓、90.8/9.2%✓、d=4.70 CI 复算✓、Table3a ΔCV −3.5%✓、coupling −30.8%✓、CNR 6.3✓。未重算：+0.207（无归档）+ d=4.85。

## TODO
1. 合并清洁：删 version note/重复段/audit-set 杂块/Phase"54"/修 extbf。
2. L675 CI 改回 overlapping；摘要+贡献与 L366 复现状态对齐（加 qwen32b 反转一句）。
3. 恢复 seed-status caveat；统一 35×/36× 与共享数值。
4. 补 GPT-4o per-rep 归档或明确不可重算。

## 备注
**正典判定**（PAPER1 vs PAPER13 同题）：完整性归 PAPER13（14250>11885 词、新增 qwen32b 复现/held-out v4-pro/定理化/ΔCV 统一），
但诚实细节互有胜负——PAPER13 引入了 PAPER1 没有的 L675 CI 矛盾、双份 novelty、Phase"54"；
PAPER1 反而有更诚实的 seed caveat。两稿皆不洁净，PAPER13 是唯一候选但必须过合并清洁。