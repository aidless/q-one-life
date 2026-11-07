# Q-One 自主代码实验闭环证据

日期：2026-11-07。模型：`group/auto-gpt-6`（本机 Magpie 网关，单次 chat 调用）。

结论：`generate -> execute -> hidden tests` 三阶段闭环真实跑通一次。

| 阶段 | 产物 | 读数 |
|---|---|---|
| 生成 | `generated.json` | code_sha256 `dde4f80487ce5acd2c74599eb65a242ff08626a255bc03a6505bae338dde68b7` |
| 沙盒执行 | `execution.json` | returncode 0, sandbox network `not_granted` |
| 隐藏测试 | `verdict.json` | 4/4 通过 |

任务：给定 `data["datasets"]["answers"]`，返回众数与非空答案数。
输入：`[2, 2, 3, None, 2]`；输出：`{"majority": 2, "count": 4}`。

## 边界

- 这是一次**有界任务**的闭环证据，不是 PaperBench 三份复现包由模型生成的证据。
- 没有让模型生成那三份提交，没有用真实 PaperBench judge，也没有花付费 API。
- 本地模型调用走 `127.0.0.1:3425` 网关；网关后端的实际计费方式未审计。

## 下一步

1. 把这一闭环作为模板：让模型生成 PaperBench 任务包，再送进 DirectSubmission + dummy judge。
2. 接入云端 GPU 做真实训练；接真实 judge 前需获得单独授权。
