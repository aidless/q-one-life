# 主机隐藏契约闸门

日期：2026-11-07。契约：`HOST_CONTRACT.json`，`host_only=true`，
`never_include_in_model_prompt=true`。契约不进入模型提示。

闸门：`scripts/verify_external_contract.py`。退出码按
`0=PASS, 1=FAIL, 2=USAGE, 3=NOT_EXECUTED`；`3` 明确记录
「闸没执行不等于通过」。

## 检查项

每个任务必须在主机侧独立通过：

- 提交目录不含隐藏契约标记；
- `run.py`、`data/sample.json`、`tests/`、`results/`、`README.md` 存在；
- `run.py < data/sample.json` 输出 JSON，且 `paper_id` 与状态字段合法；
- `pytest -q tests` 通过，主提交至少 9 项、架构桩至少 3 项；
- stdout/stderr 与运行退出码保留哈希，便于复算。

## 实测

| 环境 | 结果 | problems | tasks | ok | hidden_leaks |
|---|---|---:|---:|---:|---:|
| 本机 `/usr/bin/python3` | PASS | 0 | 10 | 10 | 0 |
| AMD 云端 `/opt/venv/bin/python` | PASS | 0 | 10 | 10 | 0 |

回执：`local-result.json`、`cloud-result.json`。

## 双向变异自测

`selftest.json`：

- 方向 A：把每个任务的执行 cwd 改成共享目录，拆掉逐包隔离。
  结果 9 个 `paper_id_mismatch`，`direction_a_problems=9`。
- 方向 B：把 `min_pytest_cases` 全部提高 1。
  结果 10 个 `pytest_case_count` 失败，`direction_b_problems=10`。
- 反夹具钉在「实际测试数 = 正确下限、且低于破坏后的下限」这一带，
  所以 B 不是装饰性绿灯。
- 恢复后 `base/restored problems=0`，`passed=true`。

## 不能声称

- 这不是 PaperBench judge，不读取 rubric 答案，不给任何叶子打通过。
- 它只证明 10 个包的统一运行契约、隐藏信息未泄漏、测试数量与入口诚实。
- 架构桩仍不覆盖训练或论文结果；所有真实分数仍为 0。
