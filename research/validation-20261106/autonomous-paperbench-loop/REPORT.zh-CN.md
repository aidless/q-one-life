# Q-One 自主项目 → PaperBench 归档闭环证据

日期：2026-11-07。模型：`group/auto-gpt-6`。

结论：`research-project generate -> verify -> build -> DirectSubmission -> dummy judge`
整条链路真实跑通一次。

| 阶段 | 证据 | 读数 |
|---|---|---|
| 生成 | `qone-pb-receipt.json` | 4 个 Python 文件，模型输出 |
| 验证 | `qone-pb-verdict.json` | 自带 3 项 + 主机隐藏 2 项，pytest 3/3，run.py 输出 `{"chosen":"1"}` |
| 构建 | `/tmp/qone-pb-build/` | 4 个文件 + `src/__init__.py` |
| 归档 | `2026-11-07T14-59-44-GMT_run-group_direct_submission_solver/semantic-self-consistency_.../submissions/*/submission.tar.gz` | 10 个 tar 条目，含 5 个 `.py` |
| 判分 | 同 run group `grade.json` | dummy score 1.0 |

## 关键边界

- 这是**模型生成的项目被上游归档**的闭环证据，不是 PaperBench 能力分数。
- 模型生成的是 `semantic-self-consistency` 的最小风格项目：答案解析、众数、CPW/SCW 的简化实现；
  不是完整论文复现，不含数据集、真实模型调用或真实 judge。
- dummy judge 固定满分，不能当能力分数。
- 本轮为归档验证，临时代替了手写 `semantic-self-consistency` 提交；仓库里的手写提交仍保留在
  `research/paperbench-submissions/semantic-self-consistency/`。

## 下一步

1. 把项目模式的输出从 4 文件扩展成完整 PaperBench 提交包（数据、复现脚本、依赖）。
2. 接云端 GPU 执行；真实训练与真实 judge 仍需单独授权。
