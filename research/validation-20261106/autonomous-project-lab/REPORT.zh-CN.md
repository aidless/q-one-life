# Q-One 自主多文件项目闭环证据

日期：2026-11-07。模型：`group/auto-gpt-6`（本机 Magpie 网关，单次 chat 调用）。

结论：`research-project generate -> verify` 闭环真实跑通一次。

| 阶段 | 产物 | 读数 |
|---|---|---|
| 生成 | `qone-project-receipt.json` | 4 个文件；manifest_sha256 可复算 |
| 验证 | `qone-project-verdict.json` | pytest 7/7 通过；run.py 输出 `{"median": 3.0}` |
| 隐藏测试 | `qone-hidden-project.py` | 奇偶两组中位数，主机侧提供，未进模型 prompt |

## 与单函数闭环的区别

`code_lab` 只让模型写 `run(data)->dict`。`project_lab` 让模型写：
- `src/core.py`：项目实现
- `tests/test_project.py`：模型自带测试
- `run.py`：stdin JSON -> stdout JSON 入口
- 其余支持文件

所有 Python 文件都经过同一 blocked-import / blocked-token 检查；路径限制在
`src/`、`tests/`、`data/`、`results/` 与根 `run.py`。项目在临时目录中用
`sys.executable -m pytest` 与 `sys.executable run.py` 执行，网络未授予。

## 边界

- 生成的是**有界统计项目**，不是 PaperBench 复现包。
- 隐藏测试由主机提供；模型自带测试也算入 pytest 计数，但隐藏测试是另一条判据。
- 没有调用付费 API，没有把项目送进 PaperBench，没有接真实 judge。
