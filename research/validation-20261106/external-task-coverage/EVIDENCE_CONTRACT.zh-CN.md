# 10 任务逐叶证据合约

日期：2026-11-07。本文件是静态分诊工具，不是 judge。

生成命令：
```bash
python3 scripts/build_rubric_evidence_contract.py --output research/validation-20261106/external-task-coverage/evidence-contract.json
```

## 全局读数

- 任务数：10
- rubric 叶子：2776
- 已验证叶子：0
- 真实 judge 分数：0

| 主要载体 | 叶子数 |
|---|---:|
| `execution_log` | 1117 |
| `result_table_or_plot` | 217 |
| `source_code_or_config` | 1442 |

| 触发条件 | 叶子数 |
|---|---:|
| `needs_evaluation` | 999 |
| `needs_external_data` | 665 |
| `needs_figure_or_table` | 97 |
| `needs_judge` | 35 |
| `needs_model_or_api` | 634 |
| `needs_training` | 1013 |

## 每个任务

| paper_id | 叶子 | run.py | tests | results | source | execution | analysis |
|---|---:|---|---|---|---:|---:|---:|
| `semantic-self-consistency` | 77 | true | true | true | 50 | 21 | 6 |
| `self-expansion` | 253 | true | true | true | 70 | 159 | 24 |
| `self-composing-policies` | 275 | true | true | true | 151 | 96 | 28 |
| `fre` | 437 | true | true | true | 306 | 124 | 7 |
| `test-time-model-adaptation` | 163 | true | true | true | 86 | 36 | 41 |
| `mechanistic-understanding` | 96 | true | true | true | 36 | 44 | 16 |
| `all-in-one` | 174 | true | true | true | 92 | 62 | 20 |
| `stay-on-topic-with-classifier-free-guidance` | 121 | true | true | true | 70 | 35 | 16 |
| `lca-on-the-line` | 819 | true | true | true | 403 | 370 | 46 |
| `rice` | 361 | true | true | true | 178 | 170 | 13 |

## 合约说明

- `source_code_or_config`：需要源码、配置或单元测试等可静态检查载体。
- `execution_log`：需要真实运行日志、哈希可复算输出或独立重跑回执。
- `result_table_or_plot`：需要结果表、图、日志与从原始结果复算的数字。
- 触发条件只是文本分诊，可能重叠；一个叶子可同时需要外部数据、训练与 judge。
- 当前所有叶子的 `current_state` 都是 `unverified`；本地存在文件不等于满足 rubric。
- 该合约不调用真实 judge、不读取测试答案、不产生任何能力分数。

## 用途

1. 为下一步补实验排出优先级：先补 `source_code_or_config` 的可执行证据，
   再补 `execution_log`，最后才处理 `result_table_or_plot` 与真实 judge。
2. 防止把静态关键词共现、dummy 归档或短 CPU smoke 写成 rubric 通过。
3. 给用户一个可复算的缺口分母，而不是用 10/10 dummy score 冒充覆盖。
