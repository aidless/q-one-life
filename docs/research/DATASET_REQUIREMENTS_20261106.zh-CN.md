# AI Researcher 公开数据集需求与核验表

核验日期：2026-11-06。执行范围：只读取官方仓库/数据卡，下载有大小上限的
先导集；未训练模型、未运行 PaperBench、未投稿、未推送。

入口：[`research/validation-20261106/datasets/manifest.json`](../../research/validation-20261106/datasets/manifest.json)

## 结论

| 数据源 | 用途 | 当前状态 | 真实可取数量 | 许可 |
|---|---|---|---|---|
| PeerRead ICLR 2017 | 论文全文→人工 review score | **可用（探索级）** | 24 篇、73 条去重评分 | `unknown` |
| RIDAR RIV-Gold | 轨迹→科研诚信行为标签 | **标注与轨迹全取** | 60 条标注、60 条完整轨迹 | MIT |
| PaperBench | 端到端复现基准 | **任务包可读、未执行** | dev 1 题正文 + 100 节点 rubric | 代码 MIT；论文/rubric `unknown` |
| sklearn 1.9.1 三套 | 轻量开发/软件验证 | **沿用用户本地导出** | breast 569、wine 178、diabetes 442 | 代码 BSD-3；UCI 数据 CC-BY-4.0；diabetes `unknown` |

PeerRead 已达到“至少 20 篇完整解析正文与真实人工推荐分”的先导目标，但仍是
便利样本，不是 427 篇 ICLR 2017 的无偏抽样。先导集按官方 split 分开，且每
split 为 4 篇录用 + 4 篇未录用。

## PeerRead

- 官方仓库：<https://github.com/allenai/PeerRead>
- 固定 revision：`9bb37751781a900cee9e74ec3105997732c8e8e5`
- 数据分区：官方 `train` / `dev` / `test`
- 实际数量：`train` 8 篇/25 分，`dev` 8 篇/24 分，`test` 8 篇/24 分
- 正负平衡：12 篇录用、12 篇未录用；论文 ID 三 split 不重叠
- 最小正文长度：15,191 字符（解析后的 sections，不含 references）
- 评分字段：`RECOMMENDATION`
- 评分尺度：1–10 整数；依据 PeerRead 官方论文 N18-1149 §2.1
- 置信度尺度：1–5；字段 `REVIEWER_CONFIDENCE`
- 去重：原始 148 条带分记录，排除 2 条非 `AnonReviewerN` 主体，去除 73 条
  完全重复记录，剩 73 条唯一 reviewer 记录
- `RECOMMENDATION_UNOFFICIAL`：7 条记录含该字段，**未用作目标**
- 录用标签：只用于分层抽样，**未当作评分**

可消费路径：

- 论文级配对：`research/validation-20261106/datasets/processed/peerread/paper_review_pairs.jsonl`
- 逐条 review：`research/validation-20261106/datasets/processed/peerread/reviews.jsonl`
- 单篇正文：`processed/peerread/papers/{paper_id}.json`

### 版本隐患

`submission_version_status=unknown`，`original_submission_matched_papers=0`。
解析 PDF 不能证明是评审时的原投稿版本；可能是 revision 或 camera-ready。
先导样本未发现 `Under review`/`Published as` 页眉标记，但这不能完成版本匹配。
若用于“评分是否预测真实审稿”校准，必须先补齐原投稿/修订版配对证据，或把
结论限定为“解析版本上的探索性分析”。

### 许可与隐私

PeerRead README 说明部分数据因许可限制不随仓库分发，但固定树里的 ICLR 2017
目录没有独立许可证文件；故许可记为 `unknown`，不据此再分发。派生论文文件
已去掉作者和邮箱，并对邮箱/常见密钥模式做模式清洗；不宣称穷尽去标识。

### 为什么不能直接做无偏校准

- 24/427 篇是便利样本，不是随机样本。
- 解析质量存在差异；先导件只强制了最少 3 节、2,000 字符，实际最小 15,191。
- 每篇只有 3 个左右官方匿名评审，分数是序数，不应默认等距连续。
- 录用/未录用各 12 篇只控制大类平衡，不代表分数分布或主题分布平衡。

## RIDAR

- 代码：<https://github.com/THU-KEG/RIDAR>
- 代码 revision：`86aff63bc72dcbb4899aa04102fd9fd9df233dd7`
- 数据：<https://huggingface.co/datasets/THU-KEG/RIDAR>
- 数据 revision：`5ca10637e5a74fc20643000b799551b0a27cd92b`
- 官方论文：<https://arxiv.org/abs/2610.31372v1>
- 2026 标识已实际核验：页面标题为 “RIDAR: Safeguarding Research Integrity
  in Autonomous Research Agents via Automated Detection and Runtime
  Intervention”，日期 `2026/10/22`
- 许可：MIT；证据为仓库 `LICENSE` 和数据卡
- 标注：RIV-Gold 全部 60 条已下载；319 个 behavior 实例、766 个 act
- 完整轨迹：**60/60 全部下载**（2026-11-06 补齐），61,459,066 bytes，
  47,797 条记录，3,461 个 evidence span，0 个越界 span
- 类别分布：14 类中 13 类在数据中出现；`evaluator_tampering` 无任何标注样本
- 最高频是 `scientific_reporting_manipulation`（57/60 条轨迹、309 acts），
  其次 `contribution_inflation`（47/60、102 acts）
- 标签路径：`processed/ridar/paired_trajectories.jsonl`

`unknown`：缺失的 behavior key 是否等价于负例；作者是否提供固定
train/dev/test；图像附件是否构成完整证据；模型检测输出不得替代人工标签。
全部轨迹已下载，但没有训练或评测检测器；本轮只做了标签结构与检查范围审计
（`research/validation-20261106/ridar-audit/audit.json`）。

关键结论：Q-One 已实现的 6 个确定性检查消费的是稿件、账本、预注册、作业
规格和评估器文件，**没有一个消费 agent 轨迹**，因此对 RIDAR 的轨迹级检出率
目前是 0 覆盖，不能声称做过诚信检测评测。

## PaperBench

- 官方仓库：<https://github.com/openai/frontier-evals>
- 固定 revision：`b78dab1da774a6456b1ed9c48c9ff194ee3ff36d`
- 官方论文：<https://arxiv.org/abs/2504.01848v1>（标题实际核验：
  “PaperBench: Evaluating AI's Ability to Replicate AI Research”，2025/04/02）
- 官方 split 盘点：`all=20`、`dev=3`、`testing=1`、`lite=5`、`human=5`、`debug=1`
- 本包选择：`semantic-self-consistency`，属于官方 `dev`
- 正文：`raw/paperbench/materialized/paper.md`，LFS pointer 已解析并核验 OID
- Rubric：100 节点、77 个叶子要求
- 代码许可：MIT；嵌入论文和 judge/rubric 注释的再分发许可：`unknown`

**没有执行端到端基准**，因此没有 PaperBench 分数。预检结论见
`research/validation-20261106/paperbench-preflight.zh-CN.md`：上游要求
Docker 三阶段容器、带 GPU 的 reproduction 容器和付费 judge API；当前 AMD
主机实测无 `docker`、无 `nvidia-smi`、无 torch，三项硬条件均不满足。
`unknown`：所选任务的实际依赖、复现预算、judge 校验提交件、以及
paper/rubric 的独立许可。

## 科研轻量数据

沿用用户已经导出并记录的 [`pilot-data/manifest.json`](../../research/validation-20261106/pilot-data/manifest.json)：

| 数据 | 行 | 特征 | 本地 SHA-256 已回验 |
|---|---:|---:|---|
| breast_cancer | 569 | 30 | 是 |
| wine | 178 | 13 | 是 |
| diabetes | 442 | 10 | 是 |

这些是 `sklearn.datasets` 1.9.1 的真实 feature/label 导出；本任务只做先行
开发与软件验证，没有用它们训练或生成基准分数。公开多年、可能已被模型记忆，
不能作为新颖发现证据。上游 UCI Breast Cancer Wisconsin (Diagnostic) 与 Wine
页面均标 CC-BY-4.0；sklearn 代码为 BSD-3-Clause；diabetes 数据许可 `unknown`。

## 2026 新颖性边界

本次只对 RIDAR（arXiv:2610.31372v1）做了实际标题/日期核验。此前助手列出的
其他 2026 系统题名一律**不因列表而成立**；未逐一核验的条目在
`manifest.json.unchecked_2026_titles` 标为范围外，不得据此建立综述事实。

## 明确缺口

- PeerRead：原投稿版本未匹配；1–10 的活体 schema 被 OpenReview challenge/
  404 阻断，只由官方论文确认；数据再分发许可 `unknown`。
- RIDAR：60 条轨迹已全部下载并核验；无固定 split；缺失类别语义 `unknown`；
  `evaluator_tampering` 无样本，无法评估该类。
- PaperBench：尚未执行；依赖、成本、完整 judge 提交件 `unknown`。
- 轻量数据：diabetes 上游许可 `unknown`；不适用于新颖性主张。
- 未做模型评分接口实现本身；本包只提供可直接接入的稳定路径与配对字段。

## 可重复命令

```bash
cd /home/liuzewen/qone-life-work

# 官方源抓取；已存在文件必须 SHA-256 一致，不覆盖
python3 research/validation-20261106/datasets/fetch_pilot.py fetch

# 重建派生索引和 manifest
python3 research/validation-20261106/datasets/build_manifest.py build

# 复验原始大小/哈希、32 MiB 上限、manifest 与派生文件
python3 research/validation-20261106/datasets/build_manifest.py verify
```

先导总量：173 个 raw 文件、16,017,614 bytes（15.28 MiB），低于 32 MiB 上限；
单 payload 文件上限 4 MiB。下载时间与每文件 SHA-256 在
`datasets/downloads.json` 及 `manifest.json.raw_files`。
