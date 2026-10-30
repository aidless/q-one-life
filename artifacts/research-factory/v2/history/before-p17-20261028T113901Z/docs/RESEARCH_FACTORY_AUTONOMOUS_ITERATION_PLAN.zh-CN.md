## 2026-10-28 第十六个 pilot：Hidden Cost of Resampling archive

- Family：`qf-the-hidden-cost-of-resampling-how-imbala-36f86aadfa`
- Project：`qp-tmlr-tmlr-p6-60e62c7566d9`
- 决策：`merge_archive` / `archived`；不生成 independent arXiv candidate
  package，不上传。
- 源身份：7 个保留版本、7 个不同 hash；canonical
  `b1ea39681d0b89002fd520f816dea590d5daccf1cea1c5c106a703c544fcefba`
  按字节保留。`arxiv/main.tex` 与 canonical 同字节，不重复计数。
- 一手撤稿令：canonical 顶部写有
  `DEPRECATED — DO NOT SUBMIT INDEPENDENTLY`；`MERGED_INTO_tmlr_p12`
  再规定不单投、不上传、不重打包、不改正文。独立打包工作到此停止。
- 合并去向：p12 目标 `b406b923...` 有 45 次 `N-sensitivity`，但题名、
  SMOTE、随机欠采样、isotonic、frozen embeddings、BGE-small-zh-v1.5、
  RF-Hybrid、MLP-Embed 等 study-specific 命中全为 0。记录为
  “merge intent present, provenance unresolved”。
- 范围冲突：canonical 为 996 样本、6 类 synthetic style-classification；
  主快照为 1,000 样本、8 类 Newsgroups/MiniLM；N-sensitivity 为另一套
  5-seed Newsgroups/BGE-zh。
- 标题/内容冲突：标题写 Resampling，但正文仅 1 次 `resampl`、0 次
  SMOTE、0 次 undersampling，没有实际重采样实验。
- 数值冲突：195431 快照 AUROC 为
  `0.8667/0.8778/0.8754/0.6601`，不是 `0.992/0.989/0.990/0.941`；
  Brier 为 `0.5752/0.4579/0.4617/0.6968`，不是
  `0.089/0.071/0.065/0.118`。
- Isotonic：RF-Hybrid ECE 降幅 24.86%，不是 99%；AUROC 变化
  `-0.0378`，不是 `0.037`。
- 显著性：15 对中 12 对 nominal，Bonferroni 后仅 10 对；正文
  corrected `12/15` 不成立。
- N-sensitivity：RF-Embed N=200 应为 `0.150`；RF-Hybrid 线性 N 相关
  `-0.666`、log10(N) `-0.884`，不是 `-0.973`；MLP 线性 N 相关
  `-0.120`，不是 `+0.078`。
- 载体：57 条全部机械 `PASS`，但 42 条语义错绑：33 quantity、
  3 model/run、6 snapshot/seed。机械通过不能替代语义绑定。
- 元数据与评审：anonymity 记录与实名作者冲突；两个 Limitations；
  no sample-size sweep 与完整 N-sensitivity 表并存；retained review
  `2/8`、D veto / reject，R16 要求 Major Revision。
- 验收：claim ledger 19 PASS / 0 FAIL / 12 WARN；19 claims 为
  7 verified / 12 blocked；project `valid=true`、`ready=false`；
  工厂 16/16 valid、0 ready、8 个内部候选包、0 上传。
- 下一步：不为 side shell 建包。只有作者决定复用内容时，才在
  canonical `tmlr_p12` 内统一范围、恢复真实 resampling 证据、修复语义
  carrier 与元数据，并对合并后的新 hash 重新评审。

### 紧接的第十七个 pilot

下一族按 review queue 选择：

- Family：`qf-calibration-fatigue-self-evaluation-frag-3c06d49517`
- Project：`qp-calibration-merged-full-from-data3-ec845c511c6b`
- 主源：`/home/liuzewen/.research/CALIBRATION_MERGED_FULL_from_data3/main.tex`
- SHA-256：`b1de3c420d53f5333d4a522d3e3856c612520667bb209273b86f7ded2af99cd4`
- 优先级：P1；机器建议 `merge`；同一标题族还有
  `/home/liuzewen/Projects/agi-paper-pipeline/runs/tmlr-calibration-merged/source/arxiv_clean/main.tex`。
- 要求：先完成 canonical/variant 对账、merge marker 与 claim/carrier
  identity 核验，再判断补证、合并或 blocked；不得先建包。


## 2026-10-28 第十五个 pilot：N-Sensitive Calibration archive

- Family：`qf-n-sensitive-calibration-of-tree-ensemble-623d15100e`
- Project：`qp-tmlr-resampling-calibration-632b05b06c33`
- 决策：`merge_archive` / `archived`；不生成 independent arXiv candidate
  package，不上传。
- 源身份：7 个保留版本，7 个不同 hash；canonical
  `4c530815218543297824cafefa9026e402c0d1fec5528c40d37aaee24b75a475`
  按字节保留在覆盖层 `evidence/upstream/main.tex`。
- 一手撤稿令：canonical 顶部写有
  `DEPRECATED — DO NOT SUBMIT INDEPENDENTLY`；`MERGED_INTO_tmlr_p12`
  再写明不再单投、不重打包、不改正文。独立打包工作到此停止。
- 合并去向冲突：标记指向 `tmlr_p12`，但命名目标
  `b406b923...` 对 study title、SMOTE、random undersampling、
  resampling audit、frozen LLM embeddings 和 synthetic
  style-classification 的命中均为 0。保留为“archive marker present,
  merge provenance unresolved”。
- 范围冲突：canonical 16 次 synthetic style-classification；4 个
  arXiv-labelled 副本共 4 次 three-real-datasets，且 E1 含
  `20ng/ag_news/dbpedia`。数据集口径没有完成统一。
- 可复算：E1 240 行 / 6 pairs；E6 400 行。K=4 RF `0.2520→0.2662`、
  MLP `0.2032→0.0702`，否定“both improve modestly”。
- 载体缺口：201 receipts = 159 PASS + 42 no-verdict（E1 26 / E6 10 /
  E8 6）；SMOTE `p=0.13`、RUS `0.395`、post-hoc `-0.003` 没有命名字段。
- 评审：retained `5/10`，建议 merge，仍 2 Major；没有绑定当前 hash 的
  独立复审。
- 验收：claim ledger 15 PASS / 0 FAIL / 4 WARN；15 claims 为 11 verified
  / 4 blocked；工厂 15/15 valid、0 ready、8 个内部候选包、0 上传。
- 下一步：不再为该 side shell 建包。只有作者决定复用内容时，才在
  canonical `tmlr_p12` 内统一数据集范围、补齐 resampling carrier 与
  42 条 verdict，并对合并后的新 hash 重新评审。

## 2026-10-28 第十四个 pilot：Merged Flagship F4

- Family：`qf-merged-flagship-f4-verification-trust-sc-88e8c3c2ce`
- Project：`qp-tmlr-f4-verification-08357385d7b0`
- 决策：`blocked`；不生成 arXiv candidate package，不上传。
- 源身份：3 个 packet variant + 1 个 mirror，共 4 个不同 hash；canonical
  `fa583f30...` 按字节保留。结构为 15 labels、28 references、0 unresolved，
  42/42 citation 可解析。
- 可复算：270-cell pilot / 10 seeds 的 mean `0.249277...`、population SD
  `0.028931...`、CI95 `[0.245827, 0.252729]`；pooled seed block 为
  `b=44/c=12/n_d=56`、`chi2=17.16`、`p=2.09e-5`。
- 不可复算：18,000 trials 仅归档 270 cells；192/144/90/40 命名的 split
  bundle 为 0/4；4 GPU-hours 无 per-family runtime carrier；`2700`、
  `0.686`、`0.002`、`1.47` 的 numeric carrier 为 0。
- F4 表：4/8 行在页面精度下不能由自身 b/c 重算；2 个 RD 分母不同；
  Finance/Mimicry 复制同一 CI，且各自点估计不在该区间内。
- 账本与基线：manifest 19 match / 7 mismatch / 5 absent / 1 no-hash；
  carrier gate 30 PASS / 0 FAIL / 2 NOT_VERIFIABLE；archived pilot
  BFCL/WebArena 为 `0.82/0.76`，real40 两族均为 `0.00`，正文为
  `0.95/1.05`。
- 身份与评审：canonical 与 arXiv author block 不同；native ledger 仍为旧值
  `n=90,P=0.2502`；retained review 为 1/10 reject，当前 hash 无新复审。
- 验收：claim ledger 21 PASS / 0 FAIL / 15 WARN；21 claims 为 6 verified
  / 15 blocked；无 candidate package，未上传。
- 下一步：恢复逐观测与逐 family runtime carrier；修复 4 个表格行、
  manifest、baseline 与作者口径；之后才可申请新的独立评审。

### 紧接的第十五个 pilot

- Family：`qf-n-sensitive-calibration-of-tree-ensemble-623d15100e`
- Project：`qp-tmlr-resampling-calibration-632b05b06c33`
- 优先级：P1；机器建议 `merge`；6 个额外源版本；人工最终处置仍为
  `unreviewed`。
- 要求：先完成 canonical source 与 variant reconciliation，再判断补证、
  合并或 `blocked`；不得以文件齐全代替逐 claim 载体。

## 2026-10-28 第十三个 pilot：Merged Flagship F2

- Family：`qf-merged-flagship-f2-k-generalization-sele-112d818110`
- Project：`qp-tmlr-f2-theory-c2a925d103e9`
- 决策：`blocked`；不生成 arXiv candidate package，不上传。
- 源身份：覆盖层核对 3 个 packet variant + 1 个 mirror，共 4 个不同 hash；
  review packet 的 `variants_to_reconcile=2` 表示相对 primary 的额外版本数，
  不是总源数。canonical `cdf8485e...` 按字节保留。
- 结构：17 unique labels、32/32 citation 可解析，但 `alg:run` 与
  `lst:runschema` 未解析；原始审计 `gate_states.structure=failed`，工厂
  claim 账本将该门记为 blocked，不沿用旧审计的引用例外。
- 数值：2,700 cells / 2,700 holds 是声明，归档仅 5 行、3 个条件且存在重复；
  `analysis_2700.json` 的 6 条件摘要与 `per_seed.jsonl` 在 4 个条件不一致；
  bootstrap 有 2 个 point 与 per-seed 均值差异超过 0.005。
- episode：只有 180 条、gamma=0.5/1.0，缺 gamma=2.0。
- real-LLM：384 archived vs 466 declared；64-call 有 1 个失败条件和 8 个恒定
  product，128-call 余 1 batch，192-call 仅 summary string。
- 效应载体：p16 无 `dz/d/ci/p` 字段；protocol 218 bytes 不含声明阈值；
  proof `0.14–0.26` 与 abstract `0.35–0.56` 冲突；7 个 flagged values 为
  0 个 executable carrier。
- 评审：保留的 review card 为 2/10 reject，当前 hash 的独立复审 open。
- 验收：claim ledger 21 PASS / 0 FAIL / 16 WARN；工厂 13/13 valid、
  0 ready、8 个内部候选包、48 blocked claims、0 上传。
- 下一步：优先修复未解析引用；重建逐 episode/逐 seed carrier；从 raw rows
  重算 bootstrap 与六条件摘要；恢复 p16/p18/p21 效应载体；再做独立评审。

### 紧接的第十四个 pilot

下一族固定为：

- Family：`qf-merged-flagship-f4-verification-trust-sc-88e8c3c2ce`
- 优先级：P1；机器建议 `merge`；3 个 variants；人工最终处置仍为
  `unreviewed`。
- 要求：先确认 canonical source 并完成 variant reconciliation，再按 claim、
  carrier、citation、compile、package、review 顺序推进；不得用文件名齐全
  代替证据可复算。

## 2026-10-28 第十二个 pilot：Memory Architecture Effects

- Family：`qf-memory-architecture-effects-on-output-le-0ea84705a9`
- Project：`qp-tmlr-paper5-consolidated-f099458d8ecd`
- 决策：`repair`，生成内部 candidate package；不授权上传。
- 源身份：4 个 packet variant + 1 个 mirror，共 5 个不同 hash；
  canonical `f926cae5...`，overlay `b2190494...`。
- 清理：移除重复 Experimental Setup、无关 calibration/self-eval 串稿、
  重复 Reproducibility、错误脚本名、`2.39` vs `2.385` 末位错误。
- 可复算：R1 90 per-seed / 9 paired contrasts；canonical contrast
  `Δ=0.0727`、`p=0.0047`、`d_z=1.178`；v4-flash 18 cells；
  Round-4 1,080 logs / 36 cells；35/35 citation。
- 阻断：authority marker 是 output-length proxy，不是 validated authority
  bias；Round-4 raw per-seed 未保留；7 条 carrier 不覆盖所有探索数；
  independent review open。
- 候选包：10 文件，26 页双跑确定性编译，archive
  `6a2eea0b03eedd2d27b3ee4f7914217fa1f31e981a6f67d30493c1bbb8ad5e2d`；
  `ready_for_upload=false`。
- 验收：P12 claim ledger 20 PASS / 0 FAIL / 4 WARN；工厂状态
  12/12 valid、0 ready、8 个内部候选包、0 上传。

### 2026-10-28 全量 Agent 处置账本

- 已生成 `artifacts/research-factory/v2/agent-dispositions.json`。
- 覆盖：131/131 个论文族。
- Agent 建议分布：`repair` 78、`merge` 51、`archive` 1、`blocked` 1。
  这是 P12 时点的快照；P13 加入后当前分布为 `repair` 78、`merge` 50、
  `archive` 1、`blocked` 2。
- 人工最终处置：`unreviewed` 131。
- `publication_ready=0`，`upload_authorized=0`。
- 后续生产规则：优先处理无包、非 merge、P0/P1 的 `repair` family；
  `merge` family 必须先确认 canonical source 并和解全部 variant。

### 紧接的第十三个 pilot

P12 已通过工厂验收，下一族固定为：

- Family：`qf-merged-flagship-f2-k-generalization-sele-112d818110`
- Project：`qp-tmlr-f2-theory-c2a925d103e9`
- 主源：`/home/liuzewen/Projects/agi-paper-pipeline/runs/tmlr-f2-theory/paper/main.tex`
- SHA-256：`cdf8485e91fe4d1861fc473d4e8f6df3b14431ac984691f529e8a2fb4c072916`
- 优先级：P1；机器建议 `merge`；人工最终处置仍为 `unreviewed`。
- 要求：核对 3 个 packet variant；先验证 K-generalization、selective
  prediction 和 self-evaluation 三条证据链，再决定 package 或 blocked。

## 2026-10-28 第十一个 pilot：Conditional Communication Effects

- Family：`qf-conditional-communication-effects-in-mul-ad96998074`
- Project：`qp-tmlr-paper13-merged-1fe996f84944`
- 决策：`blocked`；保留 canonical 正稿作为审计对象，不创建 arXiv 候选包。
- 源身份：7 个 packet variant 加 1 个 source mirror，共 8 个不同 hash；
  paper13 canonical `5a9b0ae4...`。
- 可复算：22 unique labels、33 references、40/40 citation；
  4,000 calls / 125 sessions；平衡 ANOVA `6.61 / 2.95 / 2.22`；
  E4 30-seed TV/VT reduction `30.765% / 29.348%`；landscape
  correlations `-0.989 / -0.916`；deepseek-v4-pro held-out n=3
  mean ΔECE `-0.0067`。
- 阻断：stored ANOVA `8.16 / 7.845 / 15.37` 不可由 sessions 推导；
  `SS_within=2.8975` 精确不可达。旧 source mirror 仍含
  `8.16 / 7.84 / 15.37`。
- 阻断：Face-1 C5 CAF 及其 CI 无保留数值 carrier；GPT-4o
  per-repetition ECE 从未归档，因此 `+0.207 / d=4.85 / 90.8%`
  不能独立复算。
- 评审：open，保留 6 Major findings；没有绑定当前 hash 的关闭回执。
- 验收：P11 claim ledger 15 PASS / 0 FAIL / 5 WARN；工厂状态
  11/11 valid、0 ready、7 个内部候选包、0 上传。

### 紧接的第十二个 pilot

P11 已形成可审计 blocked 处置，下一族固定为：

- Family：`qf-memory-architecture-effects-on-output-le-0ea84705a9`
- Project：`qp-tmlr-paper5-consolidated-f099458d8ecd`
- 主源：`/home/liuzewen/Projects/agi-paper-pipeline/runs/tmlr-paper5-consolidated/paper/main.tex`
- SHA-256：`f926cae5baf4a3a9ac4cbba11d6cce8ecf6206187ea25306f620550d7a7b2bd8`
- 优先级：P1；机器建议 `merge`；人工最终处置仍为 `unreviewed`。
- 要求：核对 4 个 packet variant，先验证 memory architecture 指标和
  output-length contamination controls，再决定 repair、package 或 blocked。

## 2026-10-27 第十个 pilot：Closing the Calibration Landscape

- Family：`qf-closing-the-calibration-landscape-a-mult-99bef231e5`
- Project：`qp-tmlr-closing-landscape-133137543459`
- 决策：`repair`，收敛为 bounded reproducibility failure analysis；生成内部
  候选包，但保持 0 upload。
- 源身份：packet 的 5 个 variant 加 1 个 source mirror，共 6 个不同 hash；
  canonical `8314b7b1...`，overlay `ada8019e...`。
- 可复算：15 seed 仿真 gamma 均值 0.143 / 0.719 / 0.574；11/11 carrier；
  26/26 citation；10 页 PDF 双跑一致。
- 阻断：CV 0.192 / 0.134 / 0.174 不能在四种逐 seed 定义下复算；real-API
  CG/TEE 在 15/15 seeds 上 `γ=0, H=1`；parser 静默回退 0.5；N=15 模型身份
  缺失；39.249% 属于 uncalibrated→calibrated，不属于 CG/TEE。
- 候选包：7 文件，deterministic archive
  `e733492836fc96e95e08938cb8c5cc349ba88883a9aea206a3a5e396c8fbe525`；
  `ready_for_upload=false`。
- 验收：P10 claim ledger 16 PASS / 0 FAIL / 5 WARN；工厂状态
  10/10 valid、0 ready、7 个内部候选包、0 上传。

### 紧接的第十一个 pilot

P10 已通过工厂验收，下一族固定为：

- Family：`qf-conditional-communication-effects-in-mul-ad96998074`
- Project：`qp-tmlr-paper13-merged-1fe996f84944`
- 主源：`/home/liuzewen/Projects/agi-paper-pipeline/runs/tmlr-paper13-merged/paper/main.tex`
- SHA-256：`5a9b0ae4dca8194e22e3a275819506f97e3c03a3214853a6aba4d852e3121472`
- 优先级：P1；机器建议 `merge`；人工最终处置仍为 `unreviewed`。
- 要求：独立核对全部 7 个 packet variant；先冻结 canonical source，再按
  claim、数值 carrier、citation、compile、package、review 的顺序推进。

## 2026-10-27 第九个 pilot：Calibrating the Evaluator

- Family：`qf-calibrating-the-evaluator-does-probabili-6544cd664a`
- 决策：`merge_archive`，作为 calibration-landscape 的 protocol deposit
  归档，不创建独立 arXiv 候选包。
- arXiv 身份：`2606.31371v1`；标题匹配，唯一作者 Zewen Liu；原始 Atom
  XML、HTTP 头和 SHA-256 已保存。
- 数值阻断：驱动实现 1,200 rounds、2,400 executor calls、1,800 evaluator
  calls；稿件印刷 2,400、2,400、3,600。
- 证据阻断：length-normalized 与 symmetric-LR 对照缺失；
  `experiments/calibrated_ttrl.json` 缺失；20–49% gamma 与 45–67% JSD
  没有逐 seed carrier；31% 与均值置信区间没有 raw confidence 记录。
- 模型阻断：驱动是 `deepseek-chat` / `gpt-4o`，稿件是
  DeepSeek-V4-Pro / GLM5.2。
- 合并证据：当前父稿在 Appendix B 标记 P9/P10 为 protocol deposit only；
  预期 `b1de3c...` 快照存在，但没有显式 P9 marker，不能单独证明合并完成。
- 验收：P9 claim ledger 14 PASS / 0 FAIL / 6 WARN；工厂现状为
  9/9 valid、0 ready、6 个内部候选包、0 上传。

### 紧接的第十个 pilot

P9 已通过工厂验收，因此下一族固定为：

- Family：`qf-closing-the-calibration-landscape-a-mult-99bef231e5`
- Project：`qp-tmlr-closing-landscape-133137543459`
- 主源：`/home/liuzewen/Projects/agi-paper-pipeline/runs/tmlr-closing-landscape/paper/main.tex`
- SHA-256：`8314b7b1c2e67eb266bd08c281a4f55fd48c7e920477bae9c9794143f02f3c78`
- 优先级：P1；机器建议 `merge`；人工最终处置仍为 `unreviewed`。
- 要求：5 个 variant 全部独立核验；仿真 aggregate、real-API parser fallback、
  per-seed CV 不可重算和模型身份必须作为独立证据门处理，不得跳过。

## 2026-10-27 早期基线快照（保留）

日期：2026-10-27

## 北极星

让 131 个论文族逐族获得可审计的最终处置，并把证据充分的稿件推进到
“内部 arXiv candidate package”。候选包不等于可上传，更不等于录用或发表。

每个族必须经过以下顺序：

1. 规范源身份与版本和解；
2. claim 与证据字段绑定；
3. 数值载体重算；
4. 引用与机械打包；
5. 隔离编译与确定性归档；
6. 独立 proof/method/statistics review；
7. 作者、分类、摘要、license 与上传授权。

第 1–5 步由 Agent 自主完成；第 6 步需要独立复审证据；第 7 步永远是用户门。

## 当前基线

- 131 个论文族：P0 5、P1 26、P2 57、P3 43。
- 最终 disposition：`unreviewed` 131。
- 8 个有效 pilot overlay，0 个 `ready`。
- 6 个内部 candidate package。
- 87 个测试通过；schema 17/17；依赖、编译、归档和 claim verifier 均通过。
- 当前没有一个项目满足外部上传条件。

## 未来 30 天迭代

### 第 1 周：关闭当前证据冲突

| 优先级 | 工作 | 完成标准 |
|---|---|---|
| P0 | Paper 2 proof audit | Proposition 1–3 的假设、方向、误差项有独立逐条审计 |
| P0 | Paper 2 drift 证据 | 撤回或重算 `p=0.12`，与 frozen JSON 统一 |
| P0 | Paper 2 T7 和解 | 8/11 描述与 0/20 输出统一，或降级为明确冲突 |
| P0 | Paper 2 held-out | 补齐 30–40 held-out 条件；否则正文继续限定 sample |
| P0 | f-acceptance C11 | 对 `986c0a30...` 做独立复审并绑定 hash |
| P1 | Noise Floor C02/C03 | 恢复 native source identity；补 construct-validity 证据或收窄 claim |
| P1 | Gemma C06 | 恢复远端发布源的精确字节，再建 LaTeX 源 |
| P1 | Paper35 raw evidence | 恢复 12 个 full-run raw JSONL；否则 C02–C06 继续 candidate |
| P1 | Paper35 manifest | 补齐 62 个 upstream manifest 缺失项并绑定 hash |
| P1 | Paper6 held-out | 补 held-out real-trace 与 tau/alpha sweep；否则只保留 synthetic 结果 |
| P1 | Paper6 S4 conflict | 把 S4 的 trust-mean 优势与原生 C02 冲突固定为阻塞证据 |

### 第 2 周：Top-20 批量审计

从 Top-20 中每次选择 1 个尚未覆盖的族，优先 P1 merge 族：

1. Agent Behavior Regression Testing；
2. Aggregation Methods Under Verifier Capture；
3. Calibrating the Evaluator；
4. Closing the Calibration Landscape；
5. Conditional Communication Effects。

每个族至少产出：

- `project.json` 与规范源 hash；
- `CLAIM_LEDGER.md`；
- carrier/evidence audit；
- 机械包审计与 isolated compile；
- review request；
- 一个明确 disposition：`repair`、`merge`、`archive` 或 `blocked`。

禁止把“模型评分高”或“文件齐全”直接映射为 `arxiv-ready`。

### Paper35 已完成的第七个样板

- `source/main.tex`：`77f690d4...`；规范上游：`d1eac668...`。
- `CLAIM_LEDGER.md`：11 PASS / 0 FAIL / 4 WARN；仅 C01、C07 为 verified。
- `reports/carrier-audit.md`：8/8 carrier PASS；13/13 citation key 解析。
- `reports/cleanroom/receipt.json`：12 页、两次 PDF hash 一致。
- `reports/package/package-receipt.json`：9 文件确定性候选包，
  `76d6a559...`；未上传。
- 硬阻塞：12 个 full-run raw JSONL 全缺失；62 个 manifest 缺失项；
  BDS 敏感性、层次推断、独立 review、metadata/license 仍未关闭。

### Paper6 已完成的第八个样板

- `source/main.tex`：`fdfdb030...`；规范上游：`42fe9b13...`。
- 4 scenarios / 7 methods / 5 seeds / 1,000 rounds 的 per-seed 重算通过；
  本地 Ollama pilot 的 7 个方法均重算为 `0.9167`，仅作描述性证据。
- S4 的 trust-mean `0.8506` 高于 majority `0.8430`，原生“所有场景
  majority 最强”的 C02 已被否定并保留为冲突。
- N=10 sweep 的 trust-median `0.7668` 高于 majority `0.6785`，
  不再声称随 N 单调增强。
- 11 条 claim：7 verified / 0 candidate / 3 blocked / 1 inconclusive；
  5 文件确定性候选包，15 页，archive hash `c0e51c1b...`；未上传。

### 第 3 周：合并与去重

- 对 55 个机器建议 `merge` 的族做版本聚类。
- 每组选规范源，记录重复、旧版和 drift 副本的 hash。
- 只有当两个版本没有独立结果时才合并。
- 保留负结果、失败探针和独有图表；不得为了减少数量删除证据。
- 合并后重新跑 claim、citation、package 和 review gate。

### 第 4 周：规模化 disposition

- 将 131 个族全部推进到至少一个可审计处置。
- 统一按 `P0 > P1 > P2 > P3`、同级别按证据成熟度排序。
- 对每族记录：
  - 规范源；
  - 证据状态；
  - 未关闭问题；
  - candidate package 是否存在；
  - 下一步责任人和验收条件。
- 目标不是 131 篇全部上传，而是 131 个族都有清楚、可复核的下一步。

## 自主迭代循环

每次 heartbeat 只推进一个最高价值的可逆步骤：

1. 刷新 `FACTORY_STATUS.md`、portfolio、triage 和当前 project validation；
2. 选择优先级最高且没有当前阻塞用户门的族；
3. 建立或修复 overlay；
4. 运行数值、引用、编译、归档和 review packet；
5. 将失败保留为 blocked，不用假设填补；
6. 更新 control plane；
7. 只有发生有意义的状态变化、完成、失败或需要用户行动时通知。

状态未变化时保持安静，不输出例行“仍在运行”。

## 量化验收

- 30 天内：`unreviewed` 从 131 降到 0。
- 30 天内：每个族至少有一个可复核 disposition。
- Top-20 每族至少一个 artifact-bound audit。
- 只有当 proof、held-out、independent review、metadata 和 license 全部绑定时，
  candidate 才可升级为 `package_ready`。
- 上传、账号、作者、license、GPU/付费资源仍是用户门，Agent 不自动执行。

## 不做什么

- 不批量把家族稿复制成“新论文”。
- 不把同一结果换标题重复投递。
- 不伪造 held-out 数据、独立评审、作者、license 或发表状态。
- 不因 download、stars、模型评分或文件数量宣称质量。
- 不在没有独立复核时宣称“顶会级”“可接收”或“arXiv-ready”。
