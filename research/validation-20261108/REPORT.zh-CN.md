# 全 10 任务复现计划执行状态（2026-11-08）

## 结论

计划的基础设施已经实现并验证到可恢复状态：`gate=BLOCKED`（退出码 4），
不是全绿，也不是失败静默。2776 个 rubric 叶子全部有终态 `blocked`，
每个任务都有 `ASSETS.json` 与 `CHECKPOINT.json`。没有把 dummy 分数、
架构桩或玩具切片写成真实复现。

## 已实现

- `src/qone_life/research_factory/free_judge_panel.py`：免费多模型 judge 面板，
  固定候选队列、结构化 JSON 解析、重试、逐模型 GO 闸门、哈希回执、
  三模型不齐即 `BLOCKED`、不含真实密钥。
- `scripts/run_free_judge_panel.py`：`probe` / `go` / `grade` 三个入口。
- `scripts/build_paperbench_leaf_ledger.py`：从 10 个 rubric 生成 2776 叶
  `leaf-ledger.json`，固定终态枚举与 `panel` 配置。
- `scripts/verify_paperbench_full10.py`：检查 2776 叶、10 任务、3 个 locked
  免费 judge、GO、资产清单、检查点、panel receipt、无 dummy、无密钥。
  `PASS=0`、`FAIL=1`、`NOT_EXECUTED=3`、`BLOCKED=4`；双向变异自测通过。
- `tests/test_free_judge_panel.py`：9 项测试全过，
  覆盖三模型同批次、缺 GO、超时重试、parse 失败、缺一模型、探针锁定、
  密钥脱敏与 GO CLI。

## 免费面板实测

- `panel-probe.json`：按固定队列探测，前三个通过者锁定：
  `opencode-zen-free/deepseek-v4.1-flash-free`、
  `openrouter/recursive/flint-v1.0:free`、
  `openrouter/xingchen-agi/xing4.0-29b-a4b:free`。
- `opencode-zen-free/crouton-alpha-free` 返回 403，未入面板，不替换挑选。
- `panel-config.json` 固定 `official=false`、`judge_type=free_multimodel`。
- `pre-go-blocked.json` 证明没有逐模型 GO 时不发任何评分调用，
  回执为 `complete=false`、`blocked_reasons=missing_user_go:*`。

## 资产与阻塞审计

- `asset-channel-audit.json`：Jigsaw、AI2 ARC、BoolQ、SciQ、LAMBADA、
  GSM8K、sbi、ImageNet 元数据通道均可达；这只是可达性，不代表下载完成。
- 实测 `ILSVRC/imagenet-1k` 数据直链与 D4RL 资源返回 HTTP 401，属于需要
  登录/条款的资源；按计划 `BLOCKED`，不用凭据绕过。
- `semantic-self-consistency` 的论文表格还需要 GPT-3.5 / GPT-4o-mini
  付费推理与精确 4/6/8-shot 提示，免费面板不等于这些模型推理，故阻塞。
- 其余任务的 GPT-2/Pythia 权重、9 个 benchmark、Simformer、sbi、timm、
  RL 环境、PPO 策略、75 个视觉/VLM 模型都未下载或训练，不伪造载体。

## 当前账本

| 指标 | 数值 |
|---|---:|
| tasks | 10 |
| rubric leaves | 2776 |
| verified | 0 |
| out_of_scope_waived | 0 |
| blocked | 2776 |
| unverified | 0 |
| real judge scores | 0 |
| official PaperBench score | 0 |

## 不能声称

- 没有完成 10 任务全复现，没有 `full_reproduction`。
- 没有真实 PaperBench judge 分数；免费面板尚未正式评分，且必须逐模型 GO。
- `bae3757` 之前的 171 项主验证闸仍独立有效，本轮新闸是额外门禁。
- 没有 push、没有改账号、没有读取或落盘任何真实 API key。

## 恢复点

1. 对三个锁定模型分别给出逐线 GO，写入 `go-receipts.json`。
2. 解除 401 门控数据或改用公开等价数据，并给出 GPU 预算与逐项下载确认。
3. 每任务按 `ASSETS.json → 云端实验 → carrier ledger → panel grade → gate`
   推进；`verify_paperbench_full10.py` 从 `BLOCKED` 退出即表示可继续。
