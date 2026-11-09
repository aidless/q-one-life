# Magpie 免费通道 SimpleJudge 冒烟（非官方）

状态：`PASS`（单叶子、单模型、非官方）

## 结论

- 用上游 `SimpleJudge`（`judge_type == "simple"`，不是 dummy scaffold）对
  `semantic-self-consistency` 的叶子 `43f23e0e-2c5b-4a2b-80ab-6cc9c62723f1`
  评分，经本地 Magpie 网关 `http://127.0.0.1:3425/v1` 调用
  `openrouter/recursive/flint-v1.0:free`，返回 `score=1`、`valid_score=true`。
- `file_selection_s=20.07`、`grade_leaf_s=169.66`；主评测调用与结构化 parse 调用均正常返回。
- 本结果只证明「SimpleJudge 能经免费网关完成一次可复算评分」。它不是官方 PaperBench
  分数，也不构成能力分数，更没有晋级任何叶子。

## 通道适配（复现时必须知道）

1. `opencode-zen-free/deepseek-v4.1-flash-free` **不能用于 SimpleJudge**。
   Magpie 会向该上游注入 shell 工具；judge / file-ranking 提示会返回
   `finish_reason=tool_calls` 且 `content=None`，导致 `ParseError` 或
   `No response received from completer for file selection`。在 parse 路径上显式
   传 `tool_choice="none"` 也不稳定。
2. `openrouter/recursive/flint-v1.0:free` 可用，但它是推理模型，`max_tokens`
   必须给足：2048 会被 reasoning token 吃满并触发
   `LengthFinishReasonError`（reasoning_tokens=2247）。当前用 8192 通过。
3. 论文正文本次截断到 16000 字符（原文件 sha256 记录在回执里），
   因此这次不是对整篇论文上下文的评分。
4. 网关不认识的模型名要在 `get_model_context_window_length` 里注册上下文长度，
   本次登记 32768。

## 判分质量限制

flint 的评分理由声称提交里「没有实际的 AQuA-RAT 数据文件」，但提交目录中确实存在
`data/aqua_test.jsonl`（130192 字节，254 行）。这说明单模型免费判分可能给出正确分数
但错误理由，不能据此晋级叶子。锁定面板仍要求三模型齐全且 spread<=0.25、mean>=0.8。

## 复现

```bash
cd /tmp/paperbench-upstream/project/paperbench
GRADER_OPENAI_API_KEY=<nonempty-placeholder> OPENAI_BASE_URL=http://127.0.0.1:3425/v1 \
  uv run python /home/liuzewen/qone-life-work/research/validation-20261108/magpie-simplejudge-smoke/run_smoke.py \
  --model openrouter/recursive/flint-v1.0:free --max-tokens 8192
```

回执：`receipt.json`（含 28 个提交文件的 sha256 清单、叶子 id、模型 id、耗时与 token 用量）。

## 双模型读数（同一叶子）

| 模型 | 结果 | 耗时 |
|---|---|---|
| `openrouter/recursive/flint-v1.0:free` | `score=1`, `valid_score=true` | grade_leaf 169.66s |
| `openrouter/xingchen-agi/xing4.0-29b-a4b:free` | `score=0`, `valid_score=true` | grade_leaf 81.29s |
| `opencode-zen-free/deepseek-v4.1-flash-free` | 通道不兼容，无法出分 | — |

spread=1.0，且只有 2/3 模型可用 → `panel-readout.json` 判 `BLOCKED`，
`promoted_leaves=0`。上游 `SimpleJudge` 因此无法完成锁定三模型面板；
替换模型属于锁定决策变更，需用户明确授权。
