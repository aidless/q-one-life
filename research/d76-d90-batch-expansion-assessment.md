# D76-D90 批次扩产评估（2026-10-30）

## 出口判据（90 天计划 §9/§10）

- [ ] 下一批 10 篇按同一流水线进入准备队列
- [ ] 0 个未关闭 P0/P1
- [ ] 复现实验记录、失败记录和包哈希齐全
- [ ] 上传仍由用户逐篇授权（用户门）

## 现状（research-triage 重跑，2026-10-30）

- 133 canonical projects（原 131 族，有少量漂移；131 族生产队列在 D1 已生成）。
- 优先级带：**P0=3、P1=30、P2=56、P3=44**。
- P0/P1 未关闭 = **33 个**（非 0），D76-D90 的「0 个未关闭 P0/P1」判据未达成。
- 机器 suggested_disposition：merge=50、repair=83；人工 final_disposition 仍全部 unreviewed（133/133）——D16-D30 人工处置未开始。
- 机器 next_actions：confirm_target_and_scope=115、run_claim_and_package_audit=14、build_bibliography=4。
- P0=3：one-rung-at-a-time-attribution、your-tool-selection-benchmark（gemma）、auditing-score-exposure（paper11）。
- P1=30：含条件通信、校准评估器、记忆架构效应、f2-k/f4 合并旗舰、n-sensitive、hidden-cost、校准疲劳、名字即接口（f-acceptance）等。

## 关键阻塞（Agent 不能自行解除）

1. **人工处置未开始**（D16-D30）：133 族全部 unreviewed。P0/P1 的关闭需要人工评审或明确的 Agent 处置授权，Agent 不擅自决定 final_disposition。
2. **下一批 10 篇入队**：machine 建议 repair/merge，但需人工确认后才有「下一批」的概念。
3. 用户门（arXiv 上传）仍逐篇授权，D76-D90 的「上传仍由用户逐篇授权」已满足（保持）。

## Agent 可推进的（机械部分）

- research-inventory + research-triage 可重跑（已做，见 /tmp/inventory.json /tmp/triage3.json），证明流水线在 133 族上可运行。
- 5 试点的证据闭环、PAPER_PLAN、独立评审、机械包评估全部完成（D31-D75）。

## 结论

D76-D90 的「0 个未关闭 P0/P1」判据**未达成**（当前 P0=3/P1=30），根因是 D16-D30 人工处置未开始（133/133 unreviewed）。这是显式报告的状态：Agent 的机械部分（inventory/triage 可运行、5 试点完成）已推进到底，剩余需要人工处置或用户授权，不属静默缺陷。下一批 10 篇的「入队」概念在人工处置后才有意义。
