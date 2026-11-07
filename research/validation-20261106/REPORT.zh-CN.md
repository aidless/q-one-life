# Q-One AI 研究员先导验证报告

日期：2026-11-06。状态：先导实验完成，结果不支撑“多智能体优于单智能体”的论断。
范围：固定算法族与参数搜索的受控研究闭环，不是通用自主科学家评测。

## 结论

1. 54 条真实云端轨迹全部执行，44 条完成，10 条 inconclusive；10 条全部由模型
   输出的格式或字段契约违规导致，不是训练或回执故障。
2. 完成轨迹中 0 条输出哈希不符、0 条独立重跑不一致、0 条把测试集用于选择。
3. 10 组 task/seed 完整配对里，多智能体相对单智能体 3 胜 5 负 2 平
   （精确符号检验 p=0.73）；相对 no_rebuttal 2 胜 4 负 4 平（p=0.69）。
   没有可分辨优势。
4. 乱序标签负对照的中位表观增益为 +0.004 到 +0.019，个别 seed 达 +0.052，
   说明这一量级的差异落在噪声内，不能当作方法改进的证据。
5. 注入式故障测试 10/10 检出，2 个正常对照放行。PeerRead 外部检查
   ρ=0.556（bootstrap 95% CI 0.21–0.79），只作探索证据，不构成校准证书。

## 运行身份

| 项 | 值 |
|---|---|
| 云端主机 | `36.150.116.206:36095`（AMD 实例，独立依赖目录） |
| 执行目录 | `/root/qone-validation-20261106-lab01/cloud-full-v3` |
| 模型 | `kiro/deepseek-3.2`，temperature 0，每次最多 1100 输出 token |
| runner SHA-256 | `2d13756e2fca2b3b98098a80e1d6e93fcf4db66a6d9d13f4829d62b3500cb2b7`（与本地字节一致） |
| suite SHA-256 | `258b01623706317f2bab1bbccd419b776a1e512636cec7b7bb839e78f0ed7e83` |
| 数据 manifest SHA-256 | `99c0100260caf7494ca0ad2d0ade43226af517c7860ab76a3384e86d341fef2e` |
| sklearn / Python | 1.6.1 / 3.12.3（云端） |
| 实际模型调用 | 188 次（预算上限 216） |
| 实际 token | 804,272（prompt 772,142 + completion 32,130） |
| 单条完成轨迹耗时 | 中位 48.8 s，最大 111.2 s |
| 本地回执 | `research/validation-20261106/cloud-full/` |

数据只在训练/验证集上做候选选择；测试集在全部模型调用结束后一次性评分，
并另建同参数模型独立复跑比对预测。

## 协议执行对照

| 协议块 | 执行情况 | 证据 |
|---|---|---|
| 1 来源审计 | 旧云端伪 HEAD 不追认为来源；真实 commit 另行记录 | `provenance/correction.json` |
| 2 真实闭环 | 6 任务 × 3 seed × 3 变体，真实训练与复跑 | `cloud-full/*/receipt.json` |
| 3 同预算比较 | 每条最多 4 次调用、3 个候选，单/多/无反驳同模型同预算 | `results.json` |
| 4 故障注入 | 10 类注入全部检出，2 个正常对照放行 | `cloud-full/faults.json` |
| 5 外部校准 | PeerRead 24 篇评分与人工推荐分相关，标为探索级 | `peerread-check/result.json` |

## 结果

### 配对差值

完整配对只有 10 组（54 条中 44 条完成）。逐组数据见
`results-table.md`，机器可读汇总见 `results.json`。

| 对比 | 正/负/平 | 精确符号检验 p |
|---|---|---|
| multi_agent − single_agent | 3 / 5 / 2 | 0.73 |
| multi_agent − no_rebuttal | 2 / 4 / 4 | 0.69 |

### 分任务类型的中位 test delta

| 变体 | 复现类 | 扩展类 | 乱序负对照 |
|---|---:|---:|---:|
| single_agent | +0.0238 (n=5) | +0.0482 (n=6) | +0.0094 (n=4) |
| multi_agent | +0.0119 (n=4) | +0.0375 (n=6) | +0.0040 (n=5) |
| no_rebuttal | +0.0333 (n=5) | +0.0273 (n=6) | +0.0188 (n=3) |

复现类和扩展类都是 balanced accuracy（diabetes 为 R²，单列于 `results.json`
的 `variant_stats`）。负对照的标签被随机置换，真实信号应为零；三者都出现
非零正值，说明 0.01–0.05 的差值不足以区分方法。

### inconclusive 明细

10 条全部在候选解析阶段失败，与算力、网络、回执无关：

| 失败类型 | 条数 |
|---|---:|
| `invalid candidate field types`（如 forest 给 `null` strength） | 5 |
| `strength must be finite and in [0.001,100]` | 4 |
| `model response is not JSON` | 1 |

这些失败按协议保留为 inconclusive，没有重试后当成完成。它本身是一个可引用
读数：在该结构化契约下，模型单次调用合规率约 81.5%（44/54 轨迹）。

## 故障注入

10 类注入全部检出：超时、网络失败、重跑不一致、输出缺失、非有限指标、
虚构执行、伪造 closure、字段检查 closure、评估器被替换、陈旧 closure。
2 个正常对照未被误杀。范围仅限回执/工件验证器，不等价于 RIDAR 的全类型
科研诚信检测。

## PeerRead 外部检查

- 样本：24 篇 ICLR 2017 解析正文（train/dev/test 各 8 篇，录用/未录用各半），
  73 条去重人工推荐分，尺度 1–10。
- 输入：标题、摘要、章节正文，截断到 18,000 字符；截断长度写入回执。
- 结果：加权 rubric 分与人工均分的 Spearman ρ=0.556，置换检验 p=0.0049
  （10,000 次），bootstrap 95% CI 0.21–0.79；分 split 为 0.62 / 0.44 / 0.43。
- 长度混淆检查：rubric 与正文长度 ρ=0.32（p=0.13），人工分与长度 ρ=0.32，
  未见强长度驱动。
- 录用分类：rubric 与录用标签点二列相关 0.55；人工分与录用 0.85。

限制（决定它只能是探索级）：

- 解析 PDF 未证明等于送审版本，`submission_version_status=unknown`。
- 24/427 篇是便利样本，且每 split 只有 8 篇。
- 模型可能已见过 ICLR 2017 论文与录用结果，存在预训练污染。
- 分数是序数，按 0.3/0.4/0.3 加权求和只是工程约定，不是心理测量学量表。

## RIDAR 全量轨迹审计

60 条 RIV-Gold 轨迹已全部下载并与固定 revision 的 tree 逐文件对齐：
61,459,066 bytes、60/60 文件、0 个大小或哈希问题。

| 量 | 值 |
|---|---:|
| 轨迹数 | 60 |
| 记录数 | 47,797 |
| 标注 acts | 766 |
| 证据 span | 3,461 |
| 越界 span | 0 |
| 出现的 RIVT 类别 | 13 / 14 |

最高频类别是 `scientific_reporting_manipulation`（57 条轨迹、309 acts）与
`contribution_inflation`（47 条、102 acts）；`evaluator_tampering` 没有任何
标注样本，无法评估该类。

本轮只做标签结构与检查范围审计，没有训练或评测检测器。现有 6 个确定性检查
全部消费稿件/账本/预注册/作业规格/评估器文件，没有一个消费 agent 轨迹，
因此轨迹级检出率是 **0 覆盖**，不能写成“已检测”。

### 轨迹级检测器预注册：按停线停止

在写任何检测规则之前，先冻结了 40/20 轨迹切分、规则文本、指标与停线
（`ridar-detector/PREREGISTRATION.json`）。三类候选在留出集的正例分别为：

| 类别 | 开发集 | 留出集 | 冻结下限 |
|---|---:|---:|---:|
| `exploit_test_cases` | 21 | 9 | 10 |
| `result_fabrication` | 13 | 6 | 10 |
| `citation_fabrication` | 20 | 4 | 10 |

全部低于下限，因此本轮**不可评估**，没有写检测器代码、没有调阈值、没有
产出 precision / recall。这不是“没测到”，而是按冻结协议明确停止的负结果：
当前 60 条 RIDAR 轨迹不足以对这 3 类做留出集轨迹级评估。

## 数据集：现在有什么、还缺什么

详细来源、许可与哈希见 `datasets/manifest.json` 和
`docs/research/DATASET_REQUIREMENTS_20261106.zh-CN.md`。

| 数据 | 已有 | 能支持什么 | 关键缺口 |
|---|---|---|---|
| PeerRead ICLR 2017 | 24 篇全文、73 条人工分（15.28 MiB 先导包内） | 评审分与人工推荐的外部一致性检查 | 送审版本未匹配；再分发许可未知 |
| RIDAR RIV-Gold | 60 条标注 + 60 条完整轨迹（47,797 条记录、3,461 个 span、13/14 类） | 轨迹级诚信检测的标签源 | 现有检查均为工件级，轨迹级覆盖 0；无固定 split；`evaluator_tampering` 无样本 |
| PaperBench | dev 1 题正文 + 100 节点 rubric | 端到端复现评测的接口设计 | 预检不通过：无 Docker/GPU/付费 judge 凭据 |
| sklearn 三套 | 569 / 178 / 442 行 | 软件先导与负对照 | 公开已久，存在记忆污染 |

要往下走，真正需要补的是三类数据，而不是更多同质小表格：

1. **送审版本对齐的论文—评审对**（PeerRead 原投稿 PDF 或 OpenReview 活体数据），
   用于把“解析版本上的相关性”升级为可辩护的评审校准。
2. **轨迹级检测器协议**：RIDAR 的 60 条轨迹与标签已就位，但现有 6 个检查
   全部是工件级，没有任何一个读轨迹。下一步需要先预注册检测规则与切分，
   再在同一批轨迹上报告检出与误报，而不是先写规则再看结果。
3. **可执行的端到端复现任务**（PaperBench 全量或等价基准），需要容器、依赖锁定
   和 judge 提交件；这是“自主科研”与“固定模板调参”的分界线。

## 不能声称的内容

- 不能声称多智能体角色分工提升了研究质量；本数据不支持。
- 不能反过来声称多智能体一定没有效果：完整配对只有 10 组，检验欠功效。
- 不能声称系统能自主生成任意科研代码；候选空间是固定 schema。
- 不能声称已通过外部校准；PeerRead 检查是探索性的。
- 不能声称覆盖 RIDAR 全部违规类型；故障注入只测了回执验证器。
- 不能把 54 条小数据先导外推为顶会质量、新颖性或通用自主科研能力。

当前完整可引用结论清单见
`docs/AI_RESEARCHER_CURRENT_CLAIMS.zh-CN.md`。

## 复现

两次启动失败的目录保留在云端未删除：`cloud-full/`（接口前缀写错，54 条立即
inconclusive）与 `cloud-full-v2/`（桥接进程中断）。正式结果是 `cloud-full-v3/`。

```bash
cd /home/liuzewen/qone-life-work

# 本地：重建汇总表
python3 scripts/aggregate_research_validation.py \
  --root research/validation-20261106/cloud-full \
  --suite research/validation-20261106/suite.json \
  --out-json research/validation-20261106/results.json \
  --out-md research/validation-20261106/results-table.md

# 本地：PeerRead 检查（命中缓存时不重复调用模型）
python3 scripts/peerread_rubric_calibration.py \
  --root research/validation-20261106/datasets \
  --out research/validation-20261106/peerread-check

# 云端：重跑完整矩阵（需本地模型网关与文件信箱桥接）
PYTHONPATH=deps:src OMP_NUM_THREADS=1 \
python3 -m qone_life.research_factory.research_validation run \
  --suite research/validation-20261106/suite.json \
  --data-root research/validation-20261106/pilot-data \
  --output cloud-full-v3 \
  --endpoint file:///root/qone-validation-20261106-lab01/mailbox-full-v3 \
  --workers 3
```
