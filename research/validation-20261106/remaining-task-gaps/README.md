# 剩余三个 PaperBench 任务的诚实缺口清单

日期：2026-11-07。本文只记录**未做**与**为什么没做**，不把架构桩说成复现。

## 已升级的任务

- `mechanistic-understanding`：Jigsaw 公开数据 90:10 划分 + TF-IDF `softmax(Wx)` 切片。
- `lca-on-the-line`：LCA / 信息量 / 深度 / 距离矩阵 / Algorithm 1 对齐损失，玩具类目树。
- `all-in-one`：VESDE 漂移、扩散、扰动核公式切片。
- `stay-on-topic-with-classifier-free-guidance`：CFG 推理切片（独立支线，见该提交包 README）。

`stay-on-topic-with-classifier-free-guidance` 的 CFG 切片只实现 Eq.7 的
`gamma * logits_cond + (1 - gamma) * logits_uncond`、可变的 gamma、无条件分支
从 prompt 最后 token 开始，以及 9 个 benchmark 的加载契约清单。它不下载
GPT-2/Pythia 权重，不跑 ARC/BoolQ 等 9 个数据集的 zero-shot 表格，也不提供
真实 judge 分数；该支线若未完成，任务仍按 `architecture_stub` 计。

## 仍是架构桩的三个任务

| 任务 | rubric leaves | 当前状态 | 不能闭合的原因 |
|---|---:|---|---|
| `test-time-model-adaptation` | 163 | `architecture_stub` | 需要 ImageNet-1K、timm 的 ViT-Base / ResNet50 / VisionMamba 预训练权重、LAME / T3A / TENT / CoTTA / SAR 基线、CMA-ES 与 FOA 的 prompt adaptation。云端只有 Qwen2.5-0.5B 与 tiny-gpt2，无上述权重与数据集；下载大模型权重与长时 TTA 评测需要单独授权。 |
| `rice` | 361 | `architecture_stub` | 需要 7 个非稀疏 + 2 个稀疏 RL 环境、PPO 预训练策略、StateMask / StateMask-R 解释与 fidelity score。当前无环境、无策略、无 GPU 训练预算；论文明确不检查架构但检查趋势，不能靠玩具脚本代替。 |
| `fre` | 437 | `architecture_stub` | 需要 D4RL AntMaze / Kitchen / ExORL 数据集与环境，FRE / GC-IQL / GC-BC / OPAL 网络与离线 RL 训练、5 seed × 20 rollout 评测。当前无 D4RL 数据、无训练预算。 |

## 下一步需要什么

1. 显式授权下载/使用大模型权重与公开数据集（ImageNet-1K、D4RL、SBI benchmark 等）。
2. 明确 GPU 机时上限；这三项都不是分钟级 smoke。
3. 真实 PaperBench judge 仍需要 `GRADER_OPENAI_API_KEY` 与 OpenAI 兼容
   `chat.completions.parse` 通道；本地 Magpie 网关有 134 个模型但无 o3 类模型、
   无 key，且上游 `OpenAICompletionsTurnCompleter` 直接构造 `openai.AsyncClient()`。
   在这些条件满足前，真实 judge 分数保持 0，不用 dummy 分数冒充。

## 结论

这三项没有"零成本纯算法叶子"可闭合。强行写空壳函数只会把状态从
`architecture_stub` 伪装成 `implemented`，与证据优先原则冲突。保留现状并登记
缺口，等资源与授权到位再逐个升档。
