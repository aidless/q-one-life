# 10 个外部科研任务评测计划

日期：2026-11-06；更新：2026-11-07。状态：10 个选定任务的文本与 rubric 已盘点；
3 个任务有 Q-One 提交包；仍无任何真实外部 benchmark 分数。详见
`external-task-coverage/REPORT.zh-CN.md`。

## 目标

让 AI 研究员从“固定候选调参”升级为：

1. 读取论文/任务说明；
2. 在沙盒中生成可运行实验代码；
3. 读取错误并修复；
4. 在隐藏测试或独立复算上被评分；
5. 留下完整轨迹与回执。

## 任务选择原则

- 必须有独立 evaluator；
- agent 不能直接读取测试答案；
- 每个任务必须有可复算基线；
- 优先选择低数据依赖、短运行任务；
- 不用 sklearn 小数据自证。

## PaperBench

上游 revision：`b78dab1da774a6456b1ed9c48c9ff194ee3ff36d`

本地已准备：

| 任务 | split | 状态 |
|---|---|---|
| `semantic-self-consistency` | dev | 论文、rubric 已就位 |
| `self-expansion` | dev | 论文、rubric 已就位 |
| `self-composing-policies` | dev | 论文、rubric 已就位 |

### 已验证（更新后）

- 上游代码 checkout 到固定 revision
- `pb-env:latest` 已构建；DirectSubmission + dummy judge + code-only 已跑通
- 三个 dev 任务都有可运行提交包与归档回执
- 10 个选定任务的 `paper.md` / `addendum.md` / `judge.addendum.md` 文本已按
  Git LFS OID 下载并 SHA-256 校验
- `external-task-coverage/coverage.json` 记录 rubric 叶子数、提交覆盖与 0 个真实分数

### 剩余阻断

1. 剩余 7 个选定任务尚无可运行 Q-One 提交
2. 真实 PaperBench judge 需要 API key 与费用授权
3. 真实训练需要 GPU 与完整数据集，不能由 dummy judge 替代

## PaperBench 3 个任务

`semantic-self-consistency`

- 目标：复现语义加权自一致性
- 评测：100 节点 rubric，77 个叶子要求
- 状态：任务包就位，等 `pb-env`

`self-expansion`

- 目标：复现 adapter mixture 方法
- 评测：rubric 已就位
- 状态：论文文本已校验，等 `pb-env`

`self-composing-policies`

- 目标：复现自组合策略
- 评测：rubric 已就位
- 状态：论文文本已校验，等 `pb-env`

## 剩余 7 个候选任务

| # | 任务 | 类型 | 状态 |
|---|---|---|---|
| 4 | `rice` | PaperBench debug | 未下载 LFS，低优先级 |
| 5 | PaperBench lite 任务 1 | 未盘点 | 等上游数据 |
| 6 | PaperBench lite 任务 2 | 未盘点 | 等上游数据 |
| 7 | PaperBench lite 任务 3 | 未盘点 | 等上游数据 |
| 8 | PaperBench human baseline 任务 1 | 未盘点 | 等上游数据 |
| 9 | PaperBench human baseline 任务 2 | 未盘点 | 等上游数据 |
| 10 | PaperBench testing 任务 1 | 未盘点 | 等上游数据 |

## 当前结论（更新后）

- 10 个选定任务已完成文本与 rubric 覆盖盘点
- 3 个 dev 任务有提交并跑通 DirectSubmission + dummy judge 归档
- `rice` 是 debug 任务，不作为能力样本
- 静态关键词共现已单独审计，不能当 judge 分数
- 仍然没有任何一个外部任务已产生真实分数

## 验收（更新后）

1. `pb-env` 镜像构建成功：已完成
2. 3 个 dev 任务 `direct submission` 端到端跑通：已完成（dummy judge）
3. 用 Q-One project lab 生成并归档项目：已完成
4. 10 个任务形成覆盖表：已完成
5. 每个任务独立 evaluator 真实分数可复算：未完成，等待真实 judge 授权
