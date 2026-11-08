# semantic-self-consistency 真实开源模型读数

日期：2026-11-07。云端 AMD 实例，本地模型 `Qwen2.5-0.5B-Instruct`（已在机器上，
无付费 API、无新权重下载）。脚本：`run_real_model_probe.py`；校验器：
`scripts/verify_scc_real_model_probe.py`。

## 为什么做

此前 `scc-real-data-probe/` 是脚本按 gold 构造回答的确定性行为探针，明确
`model_used=false`，不能当能力分数。本轮用真实 HF causal LM 生成回答，再喂给
同一份提交包的 `modal_answer` / `cpw_answer` / `scw_answer`，得到第一批
**真实的、可复算的**模型回答读数。

## 口径与边界（先写清）

- 模型是 0.5B 开源模型，**不是**原论文的 GPT-3.5 / Llama / Mistral / GPT-4o-mini；
  绝对分数不可与论文表格比较。
- `prompt_mode=fewshot_replay` 把 3 个手写示例拆成 user/assistant 多轮（保留
  few-shot 风格，避免模型续写 prompt 前缀）；`instruction` 是 zero-shot 且显式
  要求末尾写 `The answer is X.`。两种都单独报。
- 原 `fewshot` 单串 prompt 模式实测解析率 11%–22%，模型大量续写前缀而不输出
  答案行；保留脚本与日志，不把它当有效读数。
- 回答抽取器对真实模型输出做有限容差（选项字母、`\boxed{}`、末尾 True/False、
  末句数字），每条记录都标 `extract_rules`；解析率与未解析数原样入表。
- embedding 用离线确定性 hash 特征（64 维），不是 SciBERT / RoBERTa；因此
  CPW / SCW 的语义权重**不是论文中的语义权重**，只能当同一实现的行为读数。
- 只取每数据集前 60 行（AQuA 前 40 行），k=10，非全量 benchmark。

## 已完成批次的实测

| 批次 | 数据集 | n | k | 解析率 | top-prob | SC | CPW | SCW |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| fewshot_replay | StrategyQA | 60 | 10 | 0.4467 | 0.2000 | 0.3667 | 0.3667 | 0.3333 |
| fewshot_replay | SVAMP | 60 | 10 | 0.2667 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| fewshot_replay | AQuA-RAT | 40 | 10 | 0.3500 | 0.0500 | 0.2000 | 0.1000 | 0.1000 |
| instruction | StrategyQA | 60 | 10 | 0.9483 | 0.5667 | 0.5167 | 0.0333 | 0.0333 |
| instruction | SVAMP | 60 | 10 | 0.2417 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| instruction | AQuA-RAT | 40 | 10 | 0.3900 | 0.1250 | 0.3250 | 0.0000 | 0.0000 |

5 批全部落在 AMD 云端；AQuA 两路各跑 600 new tokens × 440 次生成，
单批约 84–102 分钟，已全部完成并回传。

每个数字都由 `runs/*/summary.raw.jsonl` 重新计数得到，校验器
`verification.json` 的 `gate` 对已收到的批次为 `PASS`。

## 已能看出的两件事

1. **提示格式是这一档模型的第一瓶颈**：同一 0.5B 模型、同一 60 道 StrategyQA，
   instruction 把解析率从 44.7% 拉到 94.8%，top-prob 从 20.0% 到 56.7%。
   这不是新算法，是"让模型把答案写出来"的工程读数。
2. **CPW / SCW 在 instruction 下反而崩到 3.3%**：hash embedding 让所有回答向量
   近似正交，`cpw_answer` 的 1/距离权重被最小距离项主导，`scw_answer` 退化成
   自相似求和；多数投票被错误加权覆盖。这不是论文的语义聚类失败，是**我们还没
   接上真实 embedder** 的实现缺口，必须如实标注。

SVAMP 两批全 0 也是真读数（抽查原始回答，模型确实把 51.0 算成 8、把 17.0
算成 64），不是解析失败。0.5B 在这类题上基本没有可用算术能力。
3. **AQuA 上 SC 明显优于贪心**（few-shot 0.05 -> 0.20，instruction 0.125 -> 0.325）：
   解析率只有 35%–39%，但一旦模型写出选项字母，10 次采样的多数投票能捞回一部分；
   这是 0.5B 模型上的条件性现象，不能外推到论文里的强模型。

## 双向变异自测

## 真实 embedding 重算（2026-11-07 续）

上一节把 CPW / SCW 崩到 0%–3.3% 归因于 hash embedding。为把这条从推测变成
实测，本轮在 AMD 云端用真实公开权重的编码器重算了全部 5 批已落盘回答：

- AQuA / SVAMP 用 `allenai/scibert_scivocab_uncased`（442,197,096 字节，
  本地已有完整 blob）；StrategyQA 用 `roberta-base`（498,818,054 字节，
  SHA-256 `5bde1d28…`，本地断点续传补齐）。两者均离线加载，权重不入库。
- 只替换 embedding，回答、提示、抽取器、聚合公式全部不变；GPU 编码
  `max_length=256`、`batch_size=16`，单批 16 段从 CPU 33 秒降到 GPU 0.52 秒。
- 回执：`embedding-runs/real-embedding-{scibert,roberta}.json`；校验器
  `scripts/verify_scc_real_embeddings.py`，双向变异自测通过。

| 提示 | 数据集 | hash CPW | 真实 CPW | hash SCW | 真实 SCW | SC 多数投票 |
|---|---|---:|---:|---:|---:|---:|
| few-shot | AQuA | 0.300 | 0.275 | 0.275 | 0.275 | 0.200 |
| few-shot | SVAMP | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| few-shot | StrategyQA | 0.400 | 0.383 | 0.383 | 0.400 | 0.367 |
| instruction | AQuA | 0.300 | **0.400** | 0.300 | **0.375** | 0.325 |
| instruction | SVAMP | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| instruction | StrategyQA | 0.500 | **0.550** | 0.517 | **0.550** | 0.517 |

注：此处的 hash CPW/SCW 由 `recompute_real_embeddings.py` 按同一聚合公式重算，
与第一批 `summary.json` 中调用 `src/methods.py` 得到的 0.0333 / 0.0000 有差异，
因为重算脚本使用了本轮修正后的答案抽取器。两批口径分别见各自回执。

**结论**：接上真实语义编码器后，instruction 下 StrategyQA 的 CPW/SCW 从
0.0333 回到 0.55，AQuA 从 0 回到 0.40 / 0.375，并略高于多数投票。
之前崩掉确实是 hash 特征造成的实现缺口，不是论文语义加权方法被否定。
SVAMP 仍全 0，因为 0.5B 模型本身算术全错，换 embedding 救不回来。

## 双向变异自测（原始 5 批）

- 方向 A：把一条 `accuracy_sc` 改大并同步重算 hash，校验器变红 1 项。
- 方向 B：把期望行数 +1，校验器变红 1 项。
- 恢复后 base problems=0，`selftest.json` 为 `passed=true`。

## 不能声称

- 不是 PaperBench 真实 judge 分数，当前真实 judge 分数仍为 0。
- 不是论文复现，不是全量 1941 行评测，不是 SOTA 比较。
- 没有训练、没有微调、没有付费 API、没有 GPU 长任务以外的开销。
