# PaperBench 真实 judge 授权与通道核对

日期：2026-11-07。结论：**未运行真实 judge**，真实分数仍为 0。

## 上游代码事实

- `/tmp/paperbench-upstream/project/paperbench/paperbench/nano/eval.py:108`
  在 `get_instances()` 里硬断言 `GRADER_OPENAI_API_KEY`（或 `OPENAI_API_KEY`）非空。
- `paperbench/nano/structs.py:203` 默认 judge 是 `simple`，completer 是
  `OpenAICompletionsTurnCompleter.Config(model="o3-mini-2025-01-31", reasoning_effort="high")`。
- `common/preparedness_turn_completer/.../oai_completions_turn_completer.py:107`
  直接 `openai.AsyncClient()`，且调用 `chat.completions.parse(...)`，不是普通
  `chat.completions.create`。因此本地 Magpie 网关即使列出 134 个模型，也不能
  直接当 PaperBench judge 后端，除非它明确兼容 `parse` 与 `o3-mini` 语义。

## 本机 / 云端实测

- 本机与 AMD 云端 `GRADER_OPENAI_API_KEY`、`OPENAI_API_KEY` 都为空。
- 本机 `curl http://127.0.0.1:3425/v1/models` 返回 134 个模型，无 `o3-mini`。
- 未发现已配置的 OpenAI 兼容 key；没有用户逐线 GO，不伪造 key、不调用付费 API。

## 需要什么才能跑

1. 用户明确授权消耗付费额度，并提供可用 key（不打印、不入库）。
2. 一个支持 `chat.completions.parse` 且能承载 `o3-mini` 类推理模型的端点；
   或通过上游允许的配置把 completer 换成已验证兼容的本地/网关模型，并先做
   单 leaf 对表验证，不能默认替换后就把分数当官方 judge 分数。
3. 先跑 `paper_split=debug` 或单个任务，确认 grade.json 的 `judge_type != dummy`，
   再扩到 10 个任务。

## 不能声称

- 现有 10 个 `score=1.0` 全部来自 `judge.scaffold=dummy`，不是能力分数。
- 本报告不提供任何真实 PaperBench 分数，也不预测分数。
