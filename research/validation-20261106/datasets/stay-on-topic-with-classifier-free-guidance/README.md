# stay-on-topic-with-classifier-free-guidance 数据集与权重清单

日期：2026-11-07。PaperBench addendum 给出的官方来源如下，当前全部标记
`available=false`：没有下载、没有 GPT-2/Pythia 权重、没有 zero-shot 评测授权。

## Section 3.1 九个 zero-shot 数据源

| 数据集 | 官方 URL | 当前状态 |
|---|---|---|
| ARC-c | https://huggingface.co/datasets/allenai/ai2_arc | 未下载 |
| ARC-e | https://huggingface.co/datasets/allenai/ai2_arc | 未下载 |
| BoolQ | https://huggingface.co/datasets/google/boolq | 未下载 |
| HellaSwag | https://rowanzellers.com/hellaswag/ | 未下载 |
| PiQA | https://github.com/ybisk/ybisk.github.io/tree/master/piqa | 未下载 |
| SciQ | https://huggingface.co/datasets/allenai/sciq | 未下载 |
| TriviaQA | https://huggingface.co/datasets/mandarjoshi/trivia_qa | 未下载 |
| WinoGrande | https://huggingface.co/datasets/allenai/winogrande | 未下载 |
| LAMBADA | https://huggingface.co/datasets/EleutherAI/lambada_openai | 未下载 |

## 其他所需资源

- 模型：GPT-2 家族、Pythia 家族权重；addendum 还把 LLaMA、GPT-J、CodeGen、
  Section 3.4 人评、Section 4 VRAM 分析列为 out of scope。
- Section 3.2：GSM8K、AQuA；P3 32,902 样本（Falcon/P3 结果）。
- 评测：EleutherAI lm-evaluation-harness 或等价 harness；FLOPs 公式来自
  google-research/electra。
- 真实 judge：需要单独 key 与 OpenAI 兼容 `chat.completions.parse` 端点。

## 当前可复现的只有

`src/cfg.py` 的 Eq.7 logits 组合、可变 gamma、无条件分支起点、9 个 benchmark
的 manifest 契约。12 项测试通过（其中 9 项为本切片）。不提供任何论文表格数字。
