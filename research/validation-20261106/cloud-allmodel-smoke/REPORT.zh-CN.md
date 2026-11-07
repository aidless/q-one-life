# 模型核心提交包的云端短执行

日期：2026-11-07。远端：已授权 AMD 实例 `36.150.116.206:36095`，独立目录
`/root/qone-paperbench-20261107-smoke/job`，未触碰 `/root/qone` 与
`/root/qone-validation-20261106-lab01` 等其他作业目录。

结论：6 段全模型生成的研究逻辑在云端独立 venv 中通过测试与入口脚本。

| 项 | 读数 |
|---|---|
| 上传包 | `/tmp/qone-final-allmodel/paperbench/semantic-self-consistency/submission` |
| pytest | 6 passed |
| run.py | `{"chosen":"1","parsed":["1","1","2"],"cpw":"1","scw":"1"}` |
| src/core.py sha256 | `7a8de9ac7b8b015ec5341378ec030585341e22ba8d852a413375bbab25258ac4` |
| MANIFEST.json sha256 | `b2fe328dc4bace8c152a35c3a2f8b32ea36daf96a8aad403e43b5655f703dd92` |

## 边界

- 这是短 CPU 执行，不是 GPU 训练、不是 PaperBench 真实 judge、不是论文表格数字。
- 独立 venv 只安装 `pytest`；没有新增付费资源或账号设置。
- 远端日志仅回传 `result.log`，没有下载模型权重或大文件。

## 正式 CloudExecutor 作业

同日另用仓库自带 `src/qone_life/cloud_executor.py` 提交短作业，显式使用当前实例端口
`36095` 与独立远程根目录 `/root/qone-paperbench-20261107-smoke/executor-jobs`。

| 项 | 读数 |
|---|---|
| job_id | `qone-allmodel-cloud-20261107` |
| submit | `2026-11-07T15:45:52Z` |
| wait | `succeeded` |
| fetched files | 5 |
| status | `{"state":"succeeded","exit_code":0}` |
| outputs | pytest 6 passed、run.json、hashes.txt、result.json |

回执目录：`executor/`。该作业只做 CPU 短执行，未触碰其他并发作业、未使用 GPU、未新增付费资源。

## 决策回填

`decisions/measurements.jsonl` 记录 1 条决策与 1 条命中回执：
选择「继续接云端 CPU 短执行」，依据是可逆、零新增付费、能检验模型生成包；
实际观察为 CloudExecutor 状态 `succeeded`、6 项测试通过、入口输出符合预期。
`measure-stats` 读数 `hit_rate=1.0, matched=1, n=1`。这是单事件命中，
不是统计意义上的成功率。
