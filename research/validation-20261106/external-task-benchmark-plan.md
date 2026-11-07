# 10 个外部科研任务评测计划

日期：2026-11-06。状态：准备中；尚未产生任何外部 benchmark 分数。

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

### 已验证

- 上游代码 checkout 到固定 revision
- 依赖环境可构建
- `paper.md` 已精确下载并通过 SHA-256 校验
- `direct submission + dummy judge + code-only` 配置可进入容器启动阶段
- 本机 Docker、NVIDIA runtime、GPU 均可用

### 阻断

1. Docker daemon 无法访问 Docker Hub 拉取 `ubuntu:24.04`
2. 本机已有 14 个运行中容器，不能重启 Docker daemon
3. `pb-env:latest` 基础镜像尚未构建

### 解法

- 在一台可重启 Docker 或无业务容器的机器上构建 `pb-env`
- 或预先从代理机导入 `pb-env` 镜像 tarball
- 不需要 `paperbench` 分数，因为 dummy judge 不产生真实 benchmark 分数

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

## 当前结论

- 目前能立即纳入的是 PaperBench 3 个 dev 任务
- `rice` 是 debug 任务，不适合作为能力评测
- `lite` / `human` / `testing` 需要进一步下载和盘点
- 没有任何一个外部任务已产生真实分数

## 验收

1. `pb-env` 镜像构建成功
2. 3 个 dev 任务 `direct submission` 端到端跑通
3. 用 Q-One code lab 生成真实提交代码
4. 每个任务独立 evaluator 分数可复算
5. 10 个任务形成完整对比表
