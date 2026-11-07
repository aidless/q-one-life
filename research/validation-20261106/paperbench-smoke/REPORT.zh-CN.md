# PaperBench dev 容器冒烟成功报告（第二轮：真实提交）

日期：2026-11-07。结论：**Docker 基础设施、容器启动、提交归档、dummy judge
链路已跑通。`semantic-self-consistency` 收到包含完整复现代码的提交，dummy
judge 评分为 1.0；这是基础设施冒烟，不是真实 PaperBench 能力分数。**

## 运行身份

| 项 | 值 |
|---|---|
| 上游 revision | `b78dab1da774a6456b1ed9c48c9ff194ee3ff36d` |
| run group | `2026-11-07T10-27-44-GMT_run-group_direct_submission_solver` |
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

## 第二轮提交

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

| 任务 | 提交 | 状态 | dummy score |
|---|---|---|---:|
| `semantic-self-consistency` | 有 | 成功 grading | **1.0** |
| `self-expansion` | 无 | no checkpoint | 0.0 |
| `self-composing-policies` | 无 | no checkpoint | 0.0 |

## 重要边界

- `score=1.0` 来自 dummy judge，它对所有有效叶子固定返回 1.0。
- 不能把 1.0 写成 PaperBench 能力分数。
- 没有执行 reproduction，也没有使用真实 judge。
- 没有使用 BasicAgent 或任何付费模型。

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

1. 在云端 GPU 上运行真实的 OpenAI 兼容模型（需要付费授权与 API key）。
2. 继续构造另外 2 个 dev 任务的提交（`self-expansion`、`self-composing-policies`）。
3. 最后才评估是否接真实 judge；真实 judge 需要单独授权。

## 文件

- `direct-dummy.log`
- `pb-env-build.log`
- `image-inspect.txt`
- `2026-11-07T10-27-44-GMT_run-group_direct_submission_solver/`
