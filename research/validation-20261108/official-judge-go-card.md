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

## 需要逐线点名的 GO

1. **额度线**：明确授权消耗付费 OpenAI 兼容额度，并给出本次最大预算。
2. **凭据线**：在运行时环境中提供 `GRADER_OPENAI_API_KEY`；不打印、不入库、
   不复制到仓库、不写进日志。
3. **端点线**：提供能承载 `o3-mini-2025-01-31` 且支持
   `chat.completions.parse` 的 base URL，或逐线批准替换 completer。
4. **对表线**：先用 1 个隐藏 leaf 跑 `paper_split=debug`，确认
   `grade.json` 的 `judge_type != dummy`、分数可复算、日志无 key。
5. **扩展线**：对 10 个任务逐线 GO 后再批量跑；任一任务超时或额度耗尽即
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
- `official_scores=0`
- `dummy_scores_remain_infrastructure_only=true`
- 本卡不改变 `leaf-ledger.json`，不提升任何叶子，不调用付费 API。
