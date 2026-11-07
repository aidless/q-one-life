# PaperBench dev 冒烟报告（第三轮：三个 dev 任务全部有提交）

日期：2026-11-07。结论：**三个 dev 任务（`semantic-self-consistency`、
`self-expansion`、`self-composing-policies`）各自收到一份带可运行代码的提交，
DirectSubmission 归档与 dummy judge 全部成功。三个 1.0 都是 dummy judge 的固定
满分，不是 PaperBench 能力分数。**

## 运行身份

| 项 | 值 |
|---|---|
| 上游 revision | `b78dab1da774a6456b1ed9c48c9ff194ee3ff36d` |
| run group | `2026-11-07T14-34-31-GMT_run-group_direct_submission_solver` |
| split | `dev`（3 个任务） |
| solver | `PBDirectSubmissionSolver` |
| reproduction | skipped |
| judge | `dummy` |
| code-only | true |

## 镜像

| 镜像 | 状态 |
|---|---|
| `ubuntu:24.04` | 通过 Docker Registry API 手工下载、打包并导入 |
| `pb-env:latest` | 构建成功 |
| `alpine/socat:latest` | 通过 Docker Registry API 手工下载、打包并导入 |

`pb-env` 有一处本地构建适配：官方 Dockerfile 中 get.docker.com 官方源被网络
阻断，改为安装 Ubuntu 仓库的 `docker.io`。该适配只影响 Docker-in-Docker
安装来源；对本次 dummy/code-only 冒烟无行为影响。

`pull_from_registry` 默认值改为 `false` 只在 `/tmp/paperbench-upstream`
本地副本中，未进入 Q-One 仓库。

## 提交内容（三个任务）

- 提交目录：`/tmp/pb-submissions/semantic-self-consistency/submission`
- 代码：
  - `src/core.py`（top-prob、SC、CPW、SCW、KNN/Iso/SVM 离群点移除）
  - `src/datasets.py`（AQuA-RAT、StrategyQA、SVAMP 加载；k-shot prompt）
  - `src/embeddings.py`（SciBERT / RoBERTa-base [CLS] 向量）
  - `src/methods.py`（CPW、SCW、KNN、IsolationForest、OneClassSVM）
  - `src/utils.py`（答案解析、众数）
  - `run_experiment.py`（入口脚本）
- 数据采样文件：
  - `data/AQuA-RAT.json`（test sample）
  - `data/StrategyQA.jsonl`（test sample）
  - `data/SVAMP.jsonl`（test sample）
- 测试：`tests/test_methods.py`（9 个通过）
- mock run 结果：`results/mock.json`
- 提交归档 tar：
  `runs/.../submissions/2026-11-07T10-27-50-GMT/submission.tar.gz`

## 结果

| 任务 | 提交 | tar 条目 | dummy score |
|---|---|---:|---:|
| `semantic-self-consistency` | 有 | 36 | 1.0 |
| `self-expansion` | 有 | 20 | 1.0 |
| `self-composing-policies` | 有 | 16 | 1.0 |

每份提交都附带测试：`semantic-self-consistency` 9 项、`self-expansion` 9 项、
`self-composing-policies` 9 项，全部通过。

## 重要边界

- `score=1.0` 来自 dummy judge，它对所有有效叶子固定返回 1.0。
- 不能把 1.0 写成 PaperBench 能力分数。
- 没有执行 reproduction，也没有使用真实 judge。
- 没有使用 BasicAgent 或任何付费模型。
- `self-expansion` 与 `self-composing-policies` 只做了架构、机制、指标与
  参数增长的可运行实现；真实 CIFAR-100 / ImageNet-R / ImageNet-A / VTAB 与
  Meta-World / ALE 的训练未执行，二者都不能声称复现了论文表格数字。

## 已验证能力

1. `pb-env:latest` 可构建。
2. Alcatraz 可启动 `pb-env` 容器。
3. DirectSubmission 可把本地提交归档为 `submission.tar.gz`。
4. dummy judge 可读取归档并输出 `grade.json`。
5. 3 个 dev 任务的论文、rubric、config 和 split 可加载。
6. Q-One code lab 7 项测试可通过（`test_code_lab.py`、`test_code_lab_cli.py`）。
7. 提交包内 9 项测试可通过（`tests/test_methods.py`）。
8. mock 推理流程可运行 `run_experiment.py --lm mock --dataset svamp` 全链路。

## 下一步

1. 三个任务的真实训练都需云端 GPU：`self-expansion` 需 ViT-B/16 在 4 个基准上的
   多任务流；`self-composing-policies` 需 Meta-World/SpaceInvaders/Freeway 各 10
   seed × 1M timestep。
2. 如需真实 PaperBench 评分，需接真实 judge（需要 API key 与费用授权）。
3. 三个提交包都只覆盖 Partial 复现；接真实 judge 前应先补齐实验表格。

## 文件

- `direct-dummy.log`
- `pb-env-build.log`
- `image-inspect.txt`
- `2026-11-07T10-27-44-GMT_run-group_direct_submission_solver/`
- `2026-11-07T14-34-31-GMT_run-group_direct_submission_solver/`
- `run-3tasks.log`
