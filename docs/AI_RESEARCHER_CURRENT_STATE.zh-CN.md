# Q-One AI 研究员当前状态与下一关

日期：2026-11-07。本文只记录已落盘、可复算的状态。

## 已完成（有证据）

1. `src/qone_life/research_factory/code_lab.py` 提供有界代码生成、隔离子进程执行和主机隐藏测试；7 项仓库测试通过。
2. `research/validation-20261106/autonomous-code-lab/` 记录一次真实闭环：
   `group/auto-gpt-6` 生成代码 -> 沙盒执行 -> 4/4 隐藏测试通过。产物含代码哈希、执行回执与判定回执。
3. `research/paperbench-submissions/` 下三个 PaperBench dev 任务各有一份带测试的可运行复现包：
   `semantic-self-consistency`（9 测试）、`self-expansion`（9 测试）、
   `self-composing-policies`（9 测试）。三份都是**手写参考实现**，不是模型生成的。
4. `research/validation-20261106/paperbench-smoke/2026-11-07T14-34-31-GMT_run-group_direct_submission_solver/`
   证明三份提交都被 DirectSubmission 归档、dummy judge 正常读取并输出 grade。
5. `scripts/verify_research_validation.py` 现有 59 项机器校验，全绿。

## 不能声称

- 三个 dummy score 1.0 是 dummy judge 的固定满分，不是 PaperBench 能力分数。
- 三份提交只覆盖架构、机制、小样本冒烟与指标；没有复现论文表格里的真实数字。
- `self-expansion` 没有跑 CIFAR-100 / ImageNet-R / ImageNet-A / VTAB 上的 5-20 epoch 训练。
- `self-composing-policies` 没有跑 Meta-World / SpaceInvaders / Freeway 上的 10 seed × 1M timestep。
- 没有用真实 PaperBench judge；那需要单独授权与 API key。
- 没有把这 3 份提交交给 Q-One 自己生成；当前闭环只证明它能生成**小函数**。

## 真正卡在哪里

1. **任务形状断层**：code lab 只让模型生成单个 `run(data)->dict` 函数；PaperBench 要的是
   多文件项目、依赖、入口脚本、数据下载和长时训练。模型还没有被要求写整套项目。
2. **执行断层**：code lab 是 30 秒本地子进程；真实复现需要 Docker + GPU + 小时级训练。
   本机不是算力节点，长训练必须上云。
3. **判分断层**：目前只有 dummy judge 和自写隐藏测试。没有真实 judge，就没有能力分数。
4. **数据断层**：三份提交的数据是 manifest 或采样小文件，不是完整基准。
5. **闭环断层**：生成、归档、判分、回填迭代还没有连成一条自动链。

## 下一步（按依赖顺序，可自动化的部分）

1. 扩展 `code_lab`：新增 `project` 模式，让模型生成多文件项目，受同一沙盒契约约束。
2. 让模型生成 `semantic-self-consistency` 的一个最小提交包，跑隐藏测试，再送 DirectSubmission + dummy judge。
   这是从“小函数闭环”到“项目闭环”的第一条可测路径。
3. 把 cloud executor 接到项目模式：在 AMD / ECS / Kaggle GPU 上跑训练，产回 compact 证据。
4. 真实 judge 与真实训练都保留在用户显式 GO 之后。

## 已有命令

```bash
# 本机代码闭环测试
~/.cache/qone-life-venv/bin/python -m pytest -q tests/test_code_lab.py tests/test_code_lab_cli.py

# 三个复现包测试
python3 scripts/verify_research_validation.py --root research/validation-20261106

# 三个 PaperBench dummy judge 归档
cd /tmp/paperbench-upstream/project/paperbench
GRADER_OPENAI_API_KEY=<local-nonempty-placeholder> uv run python -m paperbench.nano.entrypoint \
  paperbench.paper_split=dev \
  paperbench.solver=paperbench.solvers.direct_submission.solver:PBDirectSubmissionSolver \
  paperbench.solver.submissions_dir=/tmp/pb-submissions \
  paperbench.reproduction.skip_reproduction=true \
  paperbench.judge.code_only=true \
  paperbench.judge.scaffold=dummy \
  runner.recorder=nanoeval.json_recorder:json_recorder
```

注意：占位 `GRADER_OPENAI_API_KEY` 只用于通过上游入口的非空校验，不会调用付费模型。
