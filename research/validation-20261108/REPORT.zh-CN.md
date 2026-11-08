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

## 用户 GO 与集成评分（2026-11-08 续）

- 用户明确"可以全部同意"，已对 3 个锁定模型写入 `go-receipts.json`，
  `batch=full10-20261108`、`budget=free-only`、`official=false`；不含 key。
- 首次真实集成评分遇到 `opencode-zen-free/deepseek-v4.1-flash-free` 对某 leaf
  返回 `tool_calls` 而 `content=null`：模型把评分当成了查文件任务。随后在
  `build_messages` 固定 system 指令禁用工具/文件访问，并请求
  `response_format=json_object`、`tool_choice=none`；新增回归测试。
- 修复后 `panel-integration-receipt.json` 对 3 个 probe leaf 完成 3 模型 ×
  3 leaf = 9 个结构化分数，`complete=true`、`official=false`、无错误。
  这是**通道集成证据**，不是任务 rubric 分数；没有复制到任务级 receipt，
  避免门禁误把它当真实 leaf 批次。
- `magpie-vendor-probe.json` 补充实测 Magpie 的 NVIDIA / AMD 相关候选：
  `openrouter/nvidia/nemotron-3.5-super-vl:free` 可用，
  `nvidia/deepseek-ai/deepseek-v4.1-flash` 与 `deepseek-ai/deepseek-v4.1-flash`
  均 60 秒超时。主面板按锁定规则不替换。

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

注：上表的 `real judge scores` 指任务 rubric 分数；通道集成回执里的 9 个
分数只验证三模型通道，不计入 2776 叶、不算 PaperBench 能力分数。

## 2026-11-08 "全做"续报

- 用户确认"可以全部同意"，3 个锁定免费模型的逐线 GO 已写入
  `go-receipts.json`；Magpie 宽探针另确认
  `openrouter/nvidia/nemotron-3.5-super-vl:free` 可用，两个 NVIDIA/DeepSeek
  通道超时，不替换锁定面板。
- 公开资产实下载：`public-benchmark-samples/` 取到 10 个 benchmark 的
  5 行样本（PiQA / P3 为 blocked），记录字节数、SHA-256 与列结构；
  `public-models-ASSET_RECEIPT.json` 记录 Pythia-70m（166,029,852 字节）
  与 GPT-2-medium（1,519,984,962 字节）公开权重全部文件的哈希。
- AMD 云端真实加载 smoke 通过：Pythia-70m 70,426,624 参数、
  GPT-2-medium 354,823,168 参数，均产出 logits（`public-models-load-smoke.json`）。
- 真实小样本切片：`cfg-public-logits.json` 给出两模型在 gamma=1/1.5 下的
  真实 CFG top-token 变化；`free-model-benchmark-smoke.json` 用免费模型在
  15 行公开样本上得 12/15；`gpt2-medium-jigsaw-probe.json` 用真实 GPT-2-medium
  残差特征在 200 行 Jigsaw 上训练线性探针，160/40 划分、准确率 0.9。
  三者都不是论文表格复现。
- 10 个任务均生成任务级 `panel-receipt.json`；其中
  `test-time-model-adaptation` 一度因 DeepSeek Free 429 连续阻塞，冷却重试后
  最终 `complete=true`。9 个任务首次完成，1 个任务经 3 次重试完成。
- `leaf-ledger.json` 对 32 个有证据的叶子记录三模型分数；22 个叶子按
  addendum 精确引用标记 `out_of_scope_waived`；其余 2754 个保持 `blocked`。
  `verified=0`：证据覆盖的是窄声明/小样本/接口载体，不满足全复现标准。
- `gate=BLOCKED`、退出码 4，问题列表为空；这表示所有叶子都有终态、
  所有任务回执齐全，但全 10 任务仍未达到 PASS 的 `verified` 门槛。

### 本轮不能声称

- 没有把 32 个叶子的三模型分数取平均或多数投票后说成 `verified`。
- 没有把 15 行公开样本、200 行 Jigsaw 或 toy logits 说成论文 benchmark。
- 没有把 gated ImageNet-1K / D4RL 的 401 用凭据绕过。
- 没有使用 `o3-mini` 或任何付费 judge；所有 judge 分数 `official=false`。

## 2026-11-08 合规公开替代续报

- `ILSVRC/imagenet-1k` 与 `timm/imagenet-1k-wds` 的 resolve 都实测返回 401 /
  "restricted, must be authenticated"，因此没有作为合规替代。
- 改用 Stanford Tiny-ImageNet-200：完整下载 248,100,043 字节，
  SHA-256 `6198c8ae…`，120,609 个 zip entries、120,000 张 64×64 图片；
  抽样 200 张覆盖 128 个类，`tiny-imagenet-sample.json` 可复算。已同步到
  `test-time-model-adaptation` / `self-expansion` / `lca-on-the-line` 的资产清单。
  它是公开视觉替代，**不是** ImageNet-1K 全量或 5 个 OOD 测试集。
- D4RL 的 HuggingFace/Minari 镜像仍 401；Berkeley 官方原始目录
  `rail.eecs.berkeley.edu/datasets/offline_rl/` 公开可达。AntMaze、Kitchen、
  MuJoCo 三个文件的 1MB Range 请求均返回 206；其中 Kitchen HDF5
  （19,560,760 字节，SHA-256 `a30382a5…`）已完整下载并解析：
  136,950 transitions、60 维观测、9 维动作、reward mean 1.3521、
  601 terminals、12 timeouts。见 `d4rl-kitchen-hdf5-structure.json`
  与 `d4rl-kitchen-data-profile.json`。
- 用 5 个公开替代资产窄声明生成 `asset-leaf-batch.json` 与对应
  `asset-panel-receipt.json`，三模型全部 `complete=true`。这些 synthetic
  asset leaf IDs 不计入 2776 rubric 叶分母。
- 所有任务资产清单已把"完全不可得"细化为"公开替代已得，训练/全量评测未完成"。
  ledger 仍为 `verified=0`、`out_of_scope_waived=22`、`blocked=2754`、
  `gate=BLOCKED`，问题列表为空。

## 2026-11-08 全量 Jigsaw 探针

- 新增 `run_gpt2_jigsaw_full.py` 与 `run_gpt2_jigsaw_sharded.sh`。首次单进程
  在 158,416/159,571 行处遇 AMD ROCm `hipErrorIllegalAddress` / `Error code 719`；
  保留失败日志，改用 20 个独立 8,000 行进程、`max_length=64`、`batch_size=8`
  绕过长时 GPU kernel 故障。
- 全量完成：159,571 行、143,614 train / 15,957 val、16,225 positives、
  `[159571, 1024]` GPT-2-medium 残差特征、20 段；
  `accuracy=0.9480478787`、`balanced_accuracy=0.813025`、
  `roc_auc=0.957871`、`elapsed_s=124.37`。
  sklearn lbfgs 有未收敛警告，已如实保留在日志，不删除。
- 7 个相关 rubric 叶子重新交给锁定三模型 judge，首次 429、冷却重试后
  `complete=true`。按 `spread <= 0.25` 且 `mean >= 0.8` 规则，
  3 个叶子升为 `verified`：Jigsaw 已切分、线性探针已评估、约 94% 验证表现。
  另外 4 个因分歧过大保留 `blocked`。
- 当前 ledger：`verified=3`、`out_of_scope_waived=22`、`blocked=2751`、
  `unverified=0`、`gate=BLOCKED`。这是第一个真实 `verified` 突破，但不等于
  任务 full_reproduction；DPO、SVD、PPLM、GPT-2 干预实验仍未做。

## 2026-11-08 三条实验线扩展

### 1. mechanistic-understanding：RTP / PPLM-style / SVD 切片

- 完整下载公开 `allenai/real-toxicity-prompts/prompts.jsonl`：
  67,690,996 字节，SHA-256 `4b680887…`。
- `run_mechanistic_extensions.py` 在 AMD 云端用 GPT-2-medium 生成 24 条 RTP
  greedy continuations、0.1 强度的 PPLM-style hidden-state steering、
  5 层 MLP value-vector SVD（`[1024,128]`）。回执
  `tasks/mechanistic-understanding/pplm-svd-slice.json` 明确
  `dpo_model_trained=false`、负样本 0 条、没有毒性评分，因此只作数据/SVD 形状证据。

### 2. Tiny-ImageNet + ConvNeXt TTA / toy LCA 小矩阵

- 用本地公开的 `timm/convnext_tiny.fb_in22k_ft_in1k` 权重
  （114,374,272 字节，SHA-256 `77b619e1…`）在 200 张 Tiny-ImageNet 图片上跑
  clean / hflip / brightness / center_crop 四种扰动。
- `clean_prediction_agreement` 为 200 / 172 / 174 / 133；toy 20-parent
  `lca_error` 为 0 / 0.14 / 0.125 / 0.33。回执
  `tiny-imagenet-tta-lca-matrix.json`。这不是 ImageNet-1K、5 个 OOD 数据集
  或 75 模型结果。

### 3. D4RL Kitchen 行为克隆

- `run_d4rl_kitchen_bc.py` 在完整 Kitchen HDF5 上训练 2×256 MLP 行为克隆：
  136,950 transitions、123,255 train / 13,695 val、5 epoch。
- `final_val_mse=0.0332668`、`final_val_mae=0.125186`、5.81 秒。
  没有在线 rollout、没有环境 return，不能当 RL 成功率。

### Judge 与判定

- 5 个实验批次首次全部因 DeepSeek Free 429 `BLOCKED`；按用户规则只冷却
  重试、不换锁定模型、不发布部分分数。重试后 5 批 `complete=true`。
- 三模型对这批窄证据普遍给低分或分歧（多数 mean < 0.8 或 spread > 0.25），
  因此**没有新增 verified 叶子**。全部原始分数与回执保留。
- 当前 ledger 保持 `verified=3`、`waived=22`、`blocked=2751`、
  `unverified=0`、`gate=BLOCKED`。

## 不能声称

- 没有完成 10 任务全复现，没有 `full_reproduction`。
- 没有真实 PaperBench judge 分数；免费面板尚未正式评分，且必须逐模型 GO。
- `bae3757` 之前的 171 项主验证闸仍独立有效，本轮新闸是额外门禁。
- 没有 push、没有改账号、没有读取或落盘任何真实 API key。

## 恢复点

1. 逐模型 GO 已完成；任务级评分仍缺 10 份真实 leaf 批次 receipt。
2. 解除 401 门控数据或改用公开等价数据，并给出 GPU 预算与逐项下载确认。
3. 每任务按 `ASSETS.json → 云端实验 → carrier ledger → panel grade → gate`
   推进；`verify_paperbench_full10.py` 从 `BLOCKED` 退出即表示可继续。
