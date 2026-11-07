# 模型辅助完整 PaperBench 提交包闭环

日期：2026-11-07。模型：`codex/gpt-6.1-sol`（本机 Magpie 网关，3 次短调用）。

结论：一份含 12 个文件的完整提交包通过 `verify -> package -> DirectSubmission -> dummy judge`。

## 来源边界

- 模型真实生成 3 个核心函数：`parse_answer`、`modal_answer`、`_hash_embed`。
  原始响应和片段哈希保存在 `model-*-raw.txt` 与 `qone-fragments.json`。
- 宿主模板补齐聚合函数、入口脚本、README、requirements、reproduce.sh、
  `src/datasets.py`、`src/embeddings.py`、`src/methods.py`、测试与样例数据。
- `qone-full-receipt.json` 的 `source_note` 明确记录这条分工。
- 这不是「模型一次性生成完整包」；长代码 prompt 在当前网关下不稳定，已保留该失败事实。

## 读数

| 阶段 | 产物 | 读数 |
|---|---|---|
| 模型片段 | `model-*-raw.txt` | 3/3 返回合规 JSON |
| 项目验证 | `qone-full-verdict.json` | pytest 8/8 通过；run.py 成功 |
| 打包 | `qone-full-package.json` | 12 文件，manifest_sha256 `f02bf47b...` |
| 归档 | `2026-11-07T15-26-43-GMT_run-group_direct_submission_solver` | semantic tar 16 条目，含 README、reproduce.sh、MANIFEST |
| 判分 | 同 run group `grade.json` | dummy score 1.0 |

## 不能声称

- dummy 1.0 不是 PaperBench 能力分数。
- 没有真实数据集、真实模型训练、真实 judge 或论文表格数字。
- 完整包中只有 3 个核心函数由模型生成，其余是宿主模板。
