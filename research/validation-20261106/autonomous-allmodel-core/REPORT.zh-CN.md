# 全模型核心逻辑 PaperBench 提交包闭环

日期：2026-11-07。模型：`codex/gpt-6.1-sol` 短调用。

结论：`src/core.py` 的 6 段研究逻辑全部由模型生成；宿主只拼接这些片段，并补齐入口、测试、数据与文档。10 个必需文件齐全，项目验证、打包、DirectSubmission 归档、dummy judge 全部成功。

## 来源边界

- 模型生成：`parse_answer`、`modal_answer`、`_hash_embed`、`cpw_answer`、
  `scw_answer`、`run`。原始响应在 `a1-*.sol.raw.txt` 与 `scw-0-*.raw.txt`。
- 宿主模板：`README.md`、`requirements.txt`、`reproduce.sh`、`run.py`、
  `src/datasets.py`、`src/embeddings.py`、`src/methods.py`、
  `tests/test_project.py`、`data/sample.json`。
- `receipt.json -> source_note` 与 `model_fragments` 逐段记录哈希。

## 读数

| 阶段 | 产物 | 读数 |
|---|---|---|
| 模型核心 | `raw-fragments.json` | 6/6 片段 |
| 验证 | `verdict.json` | pytest 8/8 通过；run.py 成功 |
| 打包 | `package.json` | 12 文件，12 个 tar 条目 |
| 归档 | `2026-11-07T15-37-44-GMT_run-group_direct_submission_solver` | semantic tar 16 条目 |
| 判分 | 同 run group `grade.json` | dummy score 1.0 |

## 不能声称

- 这不是一次性整包生成；长代码 prompt 在当前网关下不稳定，故采用逐段短调用。
- dummy 1.0 不是 PaperBench 能力分数。
- 没有真实数据集、真实论文训练、真实 judge 或论文表格数字。
