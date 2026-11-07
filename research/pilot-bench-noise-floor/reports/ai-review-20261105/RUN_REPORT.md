# AI 评审链真实旧稿验收（2026-11-05）

对象：`research/pilot-bench-noise-floor`

- 稿件：`source/main.tex`，SHA-256
  `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca`
- 账本：`CLAIM_LEDGER.md`，SHA-256
  `a58c0f13c1b6ee2bc57503cd2e05437cec3c09beaa868018dc9b5d6e3029f5e3`
- 账本解析：14 条，11 verified / 1 candidate / 2 blocked

## 1. 自动审稿

命令：`research-review`，模型 `group/auto-gpt-6`。

- 机械检查：5/6 通过；`no_blocked_claims` 失败（2 条 blocked）。
- 模型评分：novelty 3、rigor 2、clarity 2。
- 结果：`status=inconclusive`、`total=null`（机械检查未全过，拒绝给总分）。
- 回执：`review.json`，SHA-256
  `aad84fd7d67e0edf8f89d02dd65297908b8e7467b7efb956c90d0033db57097f`

## 2. 对抗评审

首次全量尝试：`group/auto-gpt-6` 额度耗尽（429），产出
`adversarial-all-inconclusive-20261106T0326Z/`，全部 inconclusive。

第二次定向尝试：`kiro/deepseek-3.2`，1 轮，仅 C02/C03/C04。

- C02 `objected`（1 条异议，boundary/hash-collision 相关）
- C03 `clean`
- C04 `clean`
- inconclusive 0
- 回执：`adversarial/summary.json`，SHA-256
  `b30e3c332911df370a7b41aa13d77d7fe31c3b6a30ae281d91324bedff64ea87`

中间失败保留：`adversarial-tooluse-20261106T0356Z/`（模型尝试读文件，
回答不是异议，已按 non-answer 记 inconclusive）。

## 3. 反驳分类

命令：`research-rebuttal`。

- executable 1（C02）
- out_of_loop 0
- unclassified 0
- 回执：`rebuttal-plan.json`，SHA-256
  `9b562548e6991d112b58aef12cd2977300eedf9524dd7523c85c7029b948181f`

## 4. 元评审决策

命令：`research-decide`。

- decision：`rollback`
- 理由：机械检查失败（`no_blocked_claims`）；1 条异议仍未关闭
- 回执：`decision.json`，SHA-256
  `7db1ac4e31cd820911bd4fa6c0993a43c54b4e2bbec5d5d9fb1c6281b85a4c31`

## 边界

- 只对 3 条论断做了对抗评审，不是全稿结论。
- 自动审稿分数不是录用结论；`total=null` 是预期行为。
- 未执行任何反驳实验，未上传、未投稿。
- 本报告只证明链路与回执可用，不证明论文质量。

## 5. C02 反驳实验

目录：`experiments/rebuttal-c02-hash-consistency/`。

脚本从 git 提交 `9eb77f1b77baaa9932d8faf18da2fc50a2077f6c` 独立恢复
`papers/bench_noise_floor/paper/main.tex`，再与当前源码和 native manifest 比对。

| 项 | 值 |
|---|---|
| Manifest / recovered | `0d68bda3…e113`（220384 bytes） |
| Current | `182822cf…3aca`（220650 bytes） |
| Manifest == recovered | true |
| Current == manifest | false |
| Diff | 8 added / 5 removed |
| Diff SHA-256 | `4df5869e9040d1579c6c1817951f737d9e1363056c3d2e8d3a17a22a740b29d8` |
| Receipt SHA-256 | `d6fdb3ef52d541c32b34f6d4bb44c6bcacb303fbbd3f1521d366d7412f8067fb` |
| Verdict | `stands` |

结论：C02 异议成立，继续 `blocked`。该实验只复核字节一致性，
不判断稿件科学质量，也不建立 publication identity。

## 6. C03 构造效度审计

目录：`experiments/rebuttal-c03-construct-audit/`。

当前源码在 “What the rule certifies” 段明确写出：规则不估计排名错误率、
不证明两个系统可区分、readable 只是引用榜首的必要条件而非排序有效的保证；
并以 100% floor 下 90%/50% 仍被拒绝为例。原 C03 的强主张措辞已不在源码中。

- Verdict：`narrowed`
- 六项文本检查全部通过
- Receipt SHA-256：`99e71d031c5c2ba582d381afebe82e9ed7802606295adc5b72e1c62212e83fa3`

C03 作为原始强主张仍记 `blocked`；收窄后的主张单列为 C15 并记 `verified`。
这是文本层面的收窄审计，不是构造效度的证明。

## 7. C04 disjoint-field 审计

目录：`experiments/rebuttal-c04-disjoint-audit/`。

`evidence/calibrated/p4_ajb_counts.json` 四臂求和为
3,020 `UNREADABLE` + 180 `MARGINAL` = 3,200 boards，`READABLE` 为 0；
正文同样报告 “0 certifications / never READABLE”。

- Verdict：`refuted`
- READABLE：0
- Receipt SHA-256：`188347628815dab345a81dafb06268de858c9f2dcededf25e95e9bb62ec207b7`

C04 状态由 `candidate` 更正为 `blocked`；实际测到的 “disjoint 部署 0 认证”
单列为 C16 并记 `verified`。这不否认部署执行过，只否认它产生过正向判决。

## 8. 全量对抗评审与异议关闭（2026-11-06）

全量 16 条、1 轮、`kiro/deepseek-3.2`：7 clean / 9 objected / 0 inconclusive。

`experiments/rebuttal-closure/` 把 6 条边界异议映射到复算回执的明确字段，
全部 `closed`：C05、C06、C07、C08、C09、C12。
剩余 objected：C02、C03、C04。

- 全量 summary：`adversarial-full/summary.json`，`c978b77b…`
- 关闭回执：`../../experiments/rebuttal-closure/results/closure.json`，`5c02cd46…`
- 更新决策：`decision-closed.json`，`rollback`（机械检查失败、3 条异议、
  11 项诚信检查未评估）

`closed` 只表示记录字段排除了该异议的替代解释，不表示科学结论已定。
