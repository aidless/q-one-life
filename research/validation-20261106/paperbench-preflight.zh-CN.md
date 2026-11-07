# PaperBench 执行预检（dev 任务 semantic-self-consistency）

日期：2026-11-06。结论：**未执行**，当前主机与凭据条件下不可运行。

## 已拿到的材料

- 固定 revision：`b78dab1da774a6456b1ed9c48c9ff194ee3ff36d`
- 论文正文：`datasets/raw/paperbench/materialized/paper.md`（含 addendum）
- Rubric：100 节点、77 个叶子要求
  （`datasets/raw/paperbench/project/paperbench/data/papers/semantic-self-consistency/rubric.json`）
- 上游 README 与许可说明：代码 MIT；嵌入论文与 rubric/judge 注释许可 `unknown`

## 上游要求的运行条件

来自固定 revision 的 `project/paperbench/README.md`：

1. `uv sync` 安装；数据用 Git LFS 单独 hydrate
   （`git lfs fetch --include "project/paperbench/data/**"`）。
2. 三阶段流程：agent rollout 在 Ubuntu 容器内产出代码库；reproduction 在
   **带 GPU 的第二个容器**里执行；grading 在第三个容器里跑 judge。
3. 需要 API key：agent 与 judge 的 `OPENAI_API_KEY` / `GRADER_OPENAI_API_KEY`，
   部分论文还需要 HuggingFace token（ImageNet、Llama-2 访问授权）。

## 本机与云端实测

| 条件 | 本机 | AMD 云端 `36.150.116.206:36095` |
|---|---|---|
| Docker | 未验证（不作为计算节点） | `docker: command not found` |
| NVIDIA GPU / 驱动 | 无 | `nvidia-smi: command not found` |
| PyTorch | 未安装 | `ModuleNotFoundError` |
| 磁盘 | 可用 | 3.5 TB，已用 1.6 TB |
| 付费 API 凭据 | 未授权使用 | 未授权使用 |

## 判定

- **不可执行**：缺少容器运行时、GPU 复现环境、付费 API 凭据三项硬条件。
- 按项目规则，购买算力、使用付费 API、上传/运行外部基准都需要逐项授权，
  因此这里只保留预检结论，不产生 PaperBench 分数。
- 论文与 rubric 的再分发许可仍为 `unknown`，即使环境就绪也不能直接公开产物。

## 若要真正跑起来，最小路径

1. 申请一台带 Docker + NVIDIA GPU 的机器（或启用当前云主机的容器与 GPU 支持）。
2. 只跑一个 dev 任务，先在 grader 之外完成 reproduction，确认能产出
   executed submission。
3. judge 阶段再决定是否接入付费 API；没有预算就停在 reproduction，
   报告“可执行但未评分”，不伪造分数。

在此之前，任何“PaperBench 得分”都不能出现在报告或简历里。
