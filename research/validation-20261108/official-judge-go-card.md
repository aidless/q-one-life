# PaperBench 官方 Judge 逐线 GO 卡

日期：2026-11-08。用户已回复“同意”。本卡只把可执行前置条件拆成可点名
的逐线动作，不把同意解释成已提供 key、已消耗付费额度或已跑出官方分数。

## 当前实测

- `GRADER_OPENAI_API_KEY`、`OPENAI_API_KEY` 在本机与 AMD 云端都为空。
- 上游 `paperbench/nano/eval.py:108` 硬断言 key 非空。
- 上游默认 `o3-mini-2025-01-31` + `reasoning_effort=high`。
- 默认 completer 调用 `chat.completions.parse(...)`；Magpie `/v1/chat/completions`
  不能等价替代。
- 当前 Magpie `/v1/models` 返回 132 个模型，未发现 `o3-mini` 类模型。
- 现有 10 个 `score=1.0` 全部来自 `judge.scaffold=dummy`。

## 2026-11-08 Magpie 配置复核

- 只读盘点 `~/.config/magpie/providers.json`、`plugin-providers.json` 与
  `plugin-auth.json`：37 个 provider、19 个 free 插件 provider、27 条插件登录态。
  部分普通 `key` 字段为空但插件登录态存在，不能用字段为空判断不可用。
- 用本地网关占位 key 实测 `openai.chat.completions.parse`：
  `opencode-zen-free/deepseek-v4.1-flash-free`、
  `openrouter/recursive/flint-v1.0:free`、
  `openrouter/xingchen-agi/xing4.0-29b-a4b:free`、
  `workbuddy/hy4free`、
  `openrouter/nvidia/nemotron-3.5-super-vl:free` 返回结构化 `parsed`。
- `o3-mini-2025-01-31` 被 Magpie 返回 `unknown_model_404`；
  `openai/gpt-6.1-terra` 受区域限制。结论是 Magpie 可做
  **非官方 free-channel simple judge 通道对表**，但仍不是官方 o3-mini judge。
- 详见 `magpie-parse-probe.json`。没有打印、复制、改写或提交任何 key。

## 需要逐线点名的 GO

1. **额度线**：若走 Magpie 免费模型，额度为 `free-only`；若走官方 judge，
   明确授权消耗付费 OpenAI 兼容额度并给出最大预算。
2. **凭据线**：Magpie 免费通道只需进程内非空占位 key；官方 judge 需运行时
   `GRADER_OPENAI_API_KEY`。两者都不打印、不入库、不写进日志。
3. **端点线**：Magpie `http://127.0.0.1:3425/v1` 已实测支持普通
   `chat.completions.parse`；官方 judge 仍需能承载 `o3-mini-2025-01-31` 且支持
   `chat.completions.parse` 的 base URL，或逐线批准替换 completer。
4. **对表线**：先用 1 个隐藏 leaf 跑 `paper_split=debug` 或单 leaf simple judge，确认
   `grade.json` 的 `judge_type != dummy`、分数可复算、日志无 key。
5. **扩展线**：对 10 个任务逐线 GO 后再批量跑；免费通道分数统一标记
   `official=false`、`panel=free_magpie_parse`，不得冒充官方 o3-mini 分数。
   任一任务超时或额度耗尽即
   `BLOCKED`，不取平均、不补模型、不发布部分分数。

## 可执行命令模板

以下命令只在 1-5 全部逐线 GO 后运行；`<base_url>` 与 key 由运行环境注入，
不写进仓库。

```bash
cd /tmp/paperbench-upstream/project/paperbench
GRADER_OPENAI_API_KEY="$GRADER_OPENAI_API_KEY" \
OPENAI_BASE_URL="<base_url>" \
uv run python -m paperbench.nano.entrypoint \
  paperbench.paper_split=debug \
  paperbench.solver=paperbench.solvers.direct_submission.solver:PBDirectSubmissionSolver \
  paperbench.solver.submissions_dir=/tmp/pb-submissions \
  paperbench.reproduction.skip_reproduction=true \
  paperbench.judge.code_only=true \
  runner.recorder=nanoeval.json_recorder:json_recorder
```

## 当前状态

- `official_judge_status=BLOCKED`
- `free_channel_parse_status=CHANNEL_PROVEN`
- `official_scores=0`
- `free_channel_scores=0`
- `dummy_scores_remain_infrastructure_only=true`
- 本卡不改变 `leaf-ledger.json`，不提升任何叶子，不调用付费 API。
