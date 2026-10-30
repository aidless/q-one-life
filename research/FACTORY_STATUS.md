# Research Factory status

日期：2026-10-28

## Revision candidate R3 - Benchmark Noise Floor

- 新增 `research/pilot-bench-noise-floor/revisions/2026-10-29-support-threshold-r3/`：
  在 R2 之上集成 A3 的共同支持集结果与 A4 的阈值/接口语义，不覆盖规范稿。
  R3 源码 SHA-256 为 `a9eef802...e0bb6`，与 R2 的 diff 为
  `42e40ab0...a14`，与规范稿的 diff 为 `0264a11f...3e40`。
- R3 把重复竞争的 equality 指令统一为 `leader - floor >= delta`，明确
  `delta = 2.0` 是硬编码常量、等号进入 `READABLE`，并明确置信区间只打印
  不参与判决；A3 的 joint-support LOO 归零结果和 54 题 preference 描述性
  限制已写入候选稿。
- 机械门禁：11 文件包审计通过；两次隔离编译得到逐字节相同的 46 页 PDF
  `43970817...396e`；反向覆盖为 355 readings / 352 bound / 3 excused /
  0 unbound；anchor census GREEN 且 0 missing；判决词闸 137/137。最终源字节
  上连续重跑两次，三个文本门禁回执逐字节一致。
- `revision-manifest.json` 已按实际字节修正并重新生成，SHA-256 为
  `65c25074...29bc`；`SHA256SUMS.txt` 共 36 行，包含 manifest、源码、
  overlays、回执、review request 和编译产物，排除清单自身，逐项校验通过。
- 新增 `REVIEW_REQUEST_R3.md`（`b8eaf83c...aae2`）：把 A1-A4 逐项映射到
  可复算证据，明确 MDE 术语、生成器独立性和外部金标仍是 reviewer 问题；
  该请求包只读冻结、尚未发送给任何外部评审。
- 项目账本已登记 R3 manifest、source、两个 diff、报告、overlay、gate runner、
  六份验证回执和 checksum inventory；C14 只确认候选级机械完整性。C02 source
  identity、C03 独立方法评审、A4 的 MDE 术语与生成器独立性问题仍未关闭；
  规范稿未改写，`ready=false`、`upload_authorized=0`。

## A4 threshold and interface semantics - Benchmark Noise Floor

- 新增 `research/pilot-bench-noise-floor/experiments/threshold-interface-a4/`：
  冻结 v1.0.0（`de1cb0d6…`），runner `c996fc7b…` 两次接受运行逐字节一致，
  输出 SHA-256 为 `d2fedc88…727c`，五道预注册门全部通过。
- 原 CLI 没有 `--delta`：`--help` 不暴露该参数，显式调用以 exit 2 拒绝；
  pin 住的 `audit.py` 同时含有硬编码 `2.0` 判决分支和元数据字面量。
- 等式 fixture 的整数计数推导为 `2.0000000000000018` 点，native JSON 四舍五入
  为 `2.0`，但判决返回 `READABLE`；R2 候选稿却指示读者把 equality 视为
  `MARGINAL`。实现分支是 `margin < 2.0`，所以精确 equality 也会进入可读臂。
- 区间 fixture 的点 margin 为 `+13.6364`，95% case bootstrap 为
  `[-100.0000,+21.1240]`，native 仍返回 `READABLE`；区间只在判决后打印，
  不参与门禁。
- 三个 fail-closed 对照仍返回 `UNDECIDABLE_DOMAIN_MISMATCH`、
  `UNDECIDABLE_FLOOR_DEGENERATE`、`UNDECIDABLE_NO_READING`，说明结果不是
  “永远 READABLE”。
- Claim ledger 现为 **13 PASS / 0 FAIL / 2 WARN**，C13 为 verified。A4 证据只解决
  threshold/CLI/equality/CI 接口语义；MDE 术语、生成器独立性、C02/C03 仍未闭合。
  规范稿未改写，`ready=false`、`upload_authorized=0`。R3 必须吸收 A3+A4，
  并删除 R2 中重复、互相竞争的 equality 修法句子。

## A3 k-fold common support - Benchmark Noise Floor

- 新增 `research/pilot-bench-noise-floor/experiments/kfold-common-support-a3/`：
  冻结预注册 v1.0.0（`bacdf9e0…`），在四个固定 m25 载体上重算 k-fold 与 LOO。
  runner `9669db54…` 的两次接受运行逐字节一致，输出 SHA-256 为
  `93455b86…e6391`，五道预注册门全通过。
- 症状精确复现：coherence 的 leaky `LOO_on_kfold_domain` 仍为 leader
  `83.168317`、floor `82.697201`、margin `+0.471116`（404 题）。把主金标、
  每个生成者自己的 LOO 金标、fold 金标和所有 actor 行取交集后，四项 LOO
  margin 全部精确为 `0`，bootstrap identity 2000/2000 轮为零，检查 47,200
  个标签对后 0 mismatch。
- 对照有牙：同一 joint support 上 coherence 的 k-fold margin 仍为
  `+2.872063`，95% 区间 `[+1.308815,+4.545455]`，2000/2000 轮为正；因此
  LOO 归零不是支持集修正把所有比较强制归零。
- 限制：四项 joint support 为 477 / 383 / 974 / **54** 题。preference 因 ranked
  systems 的共同作答域只剩 54 题，只能描述性使用；不能把该实验写成 k-fold
  恢复排名效度、外部有效或科学就绪。
- 状态：A3 的 support-leak 问题已有可复算答案；C02/C03 仍 blocked，A4 仍开放，
  规范稿未改写，`ready=false`、`upload_authorized=0`。

## Revision candidate R2 - Benchmark Noise Floor

- `research/pilot-bench-noise-floor/revisions/2026-10-29-estimand-split-r2/`
  已在 R1 之上生成第二个独立修订候选，不覆盖规范稿。它补上 Proposition 4
  在共享域上的零 margin 推导，并修正 A2 实际否证的 coherence 句子：2000 轮中
  有 8 轮单次抽样可分离，但不足以进入 2.5% 下尾，因此区间仍为 `[0,0]`。
- 候选源码 SHA-256：`fc24f8ef...930c0f`；机械包审计 11 files 通过，两次隔离
  编译均为 45 页且 PDF 字节一致（`17842993...e0a7`）；反向覆盖 353/350/3/0，
  判决词 136/136，anchor census GREEN。
- `revision-manifest.json` 绑定父候选 R1、规范稿、A2 预注册/runner/双跑/原生重跑、
  独立评审及五道验证回执；`SHA256SUMS.txt` 共 29 项，逐项校验通过。manifest
  SHA-256 为 `db7df4ba...2c18`。
- 边界不变：R2 只是内部候选；C02 source identity、C03 独立方法评审仍 blocked，
  A3（k-fold 共同支持集）和 A4（阈值/接口语义）仍开放；编译和门禁通过不等于
  科学就绪、录用或可上传，`ready=false`、`upload_authorized=0`。

## A2 estimand split - Benchmark Noise Floor

- 新增 `research/pilot-bench-noise-floor/experiments/bootstrap-estimand-a2/`：
  把独立评审 A2 拆成两个共享输入、不同目标的统计量。`theta_fixed` 固定点估计
  榜首、每轮只重选地板（native 打印的就是它）；`theta_both` 每轮同时重选榜首。
- 四个 m25 语料上 `theta_both` 在 2000/2000 轮严格为 0，区间退化为 `[0,0]`；
  `theta_fixed` 复现记录中的 native 区间 `[-3.90,0.00]` / `[0.00,0.00]` /
  `[-0.71,0.00]` / `[-1.73,0.00]`，且任何一轮都不为正。
- 两个反证控制（加入非生成者榜首、把榜首移出榜单但仍留在金标池）把同一统计量
  推到 `[+3.27,+7.35]` 与 `[-2.68,0.00]`，说明 `[0,0]` 不是构造自动产物。
- 保真链：未改动的 native `audit.py` 在重建输入表上重跑，产物与
  `evidence/m25_factuality.json` **逐字节相同**（`e9b7a6ec…`）；两次接受运行
  也逐字节相同（`4b0d6506…`）。
- 预注册 v2.0.0；三次失败尝试（`out` 数组尺寸、控制键名、控制构造与符号规则）
  连同日志与哈希保留在 `attempts/`，均不作为证据。
- 边界：A2 只解决"打印区间属于哪个估计目标"与标签问题；A3（k-fold 共同支持集）、
  A4（阈值与接口语义）仍开放，C02/C03 仍 blocked，`ready=false`、上传授权仍为 0。

## Revision candidate R1 - Benchmark Noise Floor

- `research/pilot-bench-noise-floor/revisions/2026-10-28-construct-validity-r1/`
  已生成一个独立修订候选，不覆盖规范稿；它收窄 producer-baseline 的解释，
  保留原稿已报告的 calibrated arm 与 disjoint-field 3,200-board 结果。
- 候选源码 SHA-256：`842f7760...e12451`；两次隔离编译均为 45 页且字节一致；
  候选专用反向数字覆盖为 353 个读数、0 未绑定，判决词闸为 136/136。
- 先前 `.qone-revision-proposal/` 与 `drafts/` 中的工作草案保留但已标记为
  superseded：其中把 `READABLE` 误写成拒绝条件、把已测 disjoint 结果误写成
  pending，并提出无功效依据的样本量门槛。
- C02 仍 blocked；C03 仍 open。合成反例只支持 A1 的措辞收窄，不验证 native
  实现、不关闭 A2/A3/A4，也不改变 `ready=false`、`upload_authorized=0`。

## Current snapshot

- 组合队列：131 个论文族，P0 5、P1 26、P2 57、P3 43；
- 机器建议：`repair` 85、`merge` 46；pinned pilot 的通用执行建议是
  `repair`，不代表最终科学处置；
- 人工最终处置仍为 `unreviewed` 131；
- Agent 侧已给出 131/131 可审计处置：`repair` 78、`merge` 46、
  `archive` 3、`blocked` 4；发布 ready 与上传授权仍均为 0；
- 131 个族均已生成独立 review packet，Top-20 队列已落盘；
- 十七个 pilot 覆盖层全部 `valid=true`，全局 `ready` 仍为 0；
- measurement binding：17/17 项目的显式 `source#field` 已校验；新增门禁
  在首次全量回归时暴露并修复 4 个陈旧/错绑字段，之后完整验证通过；
- 内部 candidate package 8 个，尚无任何上传、录用或发表；
- 工厂总 readiness 继续保持 `null`。

## Pilot status

| Pilot | Claim 状态 | 当前工件 | 剩余硬阻塞 |
|---|---|---|---|
| Paper11 | 20 verified | 20/20 ledger PASS；隔离编译 8 页；确定性 candidate archive `17b0c8...` | final metadata、license、用户授权 |
| Benchmark Noise Floor | 11 verified / 1 candidate / 2 blocked | 569-entry native ledger；A1/A2/A3/A4 五组可复算实验；R3 candidate `a9eef8...` 连续两次 46 页确定性编译、11 文件包审计、reverse 355/352/3/0、anchor GREEN、verdict 137/137；R3 checksum inventory 35/35 | C02 本地源与 native manifest 不一致；C03 producer-baseline 概念效度；A4 的 MDE/生成器独立性异议；独立评审 open |
| f-acceptance | 11 verified / 1 candidate / 1 blocked | 13 PASS / 0 FAIL / 1 WARN；overlay 内 79/79 双跑；231/9 disjointness=0；14 页确定性编译；candidate archive `cf23a6...` | C11 独立复审未绑定当前源；作者、分类、摘要、license、上传授权 |
| Gemma Tool Selection | 7 verified / 1 blocked | 450 行、75 signature、48-row probe 与发布回执已绑定 | C06 本地源与远端发布源哈希不一致；尚无 LaTeX arXiv source |
| ARC | 9 verified / 1 inconclusive / 1 blocked | 三次提交血缘和 public score 已登记 | C09/C10 的官方评分方法与精确发布源；无 arXiv source tree |
| Paper 2 Conditional Bound | 1 verified / 11 candidate / 2 blocked | 14 PASS / 0 FAIL / 2 WARN；176/176 carrier PASS；14 页确定性编译；candidate archive `561f55...` | proof audit、held-out 30–40、p=0.12 证据冲突、T7 计数冲突、Major Revisions、metadata/license |
| Agent Behavior Regression | 2 verified / 5 candidate / 3 blocked / 1 inconclusive | 11 PASS / 0 FAIL / 4 WARN；8/8 carrier PASS；9 文件包审计；12 页确定性编译；candidate archive `76d6a5...` | 1,200-cell raw JSONL、62 个 manifest 缺失项、BDS 敏感性、层次推断、Major Revisions、metadata/license |
| Verifier Capture Aggregation | 7 verified / 0 candidate / 3 blocked / 1 inconclusive | 11 PASS / 0 FAIL / 4 WARN；4 scenarios/7 methods per-seed recompute；local pilot 0.9167 重算；5 文件包审计；15 页确定性编译；candidate archive `c0e51c...` | S4 与原生 C02 冲突；held-out real trace、tau/alpha sweep、universal/ATV claim、7 Major review、metadata/license |
| Calibrating the Evaluator | 8 verified / 1 inconclusive / 5 blocked | 14 PASS / 0 FAIL / 6 WARN；arXiv `2606.31371v1` 身份、6 个源变体与父稿 marker 已绑定；merge/archive | 印刷 2,400 rounds / 3,600 evaluator calls 与驱动 1,200 / 1,800 冲突；两套对照、逐 seed JSON、句子级机制数据与模型身份均缺证 |
| Closing Calibration Landscape | 11 verified / 5 blocked | 16 PASS / 0 FAIL / 5 WARN；15 seed gamma 均值重算；11/11 carrier；26/26 citation；10 页双跑确定性编译；7 文件 candidate archive `e73349...` | CV 0.192/0.134/0.174 不可由逐 seed 复算；real-API CG/TEE 15/15 退化；N=15 模型身份缺证；39.2% 误归属；独立评审 open |
| Conditional Communication Effects | 10 verified / 5 blocked | 15 PASS / 0 FAIL / 5 WARN；8 个源版本不同 hash；结构、40/40 citation、6.61/2.95/2.22 平衡 ANOVA、E4 与 landscape 重算；blocked，无包 | stored ANOVA 8.16/7.845/15.37 不可由 sessions 推导；Face-1 CAF 与 GPT-4o per-rep 缺失；旧 mirror 仍含 legacy 值；6 Major review |
| Memory Architecture Effects | 16 verified / 4 blocked | 20 PASS / 0 FAIL / 4 WARN；R1 90 条逐 seed / 9 个 paired contrast；v4-flash 18 cells；Round-4 1,080 logs / 36 cells；26 页确定性编译；10 文件 candidate archive `6a2eea...` | authority marker 不是 validated authority bias；Round-4 raw per-seed 未保留；7/7 carrier 但仍有探索数缺口；review open |
| Merged Flagship F2 | 5 verified / 16 blocked | 21 PASS / 0 FAIL / 16 WARN；4 个不同源 hash；17 labels、32/32 citation；blocked，无包 | 2 个未解析引用；2,700 cells 只存 5 行/3 条件；per-seed 摘要冲突；episodes 仅 180 且无 gamma=2.0；real-LLM 384/466；p16/p18/p21 无字段载体；review reject |
| Merged Flagship F4 | 6 verified / 15 blocked | 21 PASS / 0 FAIL / 15 WARN；270 cells / 10 seeds 和 pooled b/c 重算；42/42 citation；blocked，无包 | 18,000 trials 仅归档 270 cells；192/144/90/40 split bundle 为 0/4；4/8 表格行不可复算；manifest 19 match / 7 mismatch / 5 absent；作者元数据冲突；review reject |
| Calibration Fatigue | 8 verified / 6 blocked | 14 PASS / 0 FAIL / 6 WARN；29/29 citation；T50 120 seeds / 30,000 pairs ECE recompute；内部 8-file 修订双跑 26 页；blocked，无包 | GPT-4o Finding-1/Finding-2 raw traces；损坏 predecessor；stale outer/arXiv manifests；当前修订 hash 独立 review |


## P17 Calibration Fatigue merged manuscript

- Family `qf-calibration-fatigue-self-evaluation-frag-3c06d49517`；project
  `qp-calibration-merged-full-from-data3-ec845c511c6b`；canonical SHA-256
  `b1de3c42...`。决策仍为 `blocked` / `blocked`，无候选包、未上传。
- 纠错：上一轮称 canonical 缺两个 bib key 是扫描器误报；旧工具只读取
  `references.bib`，遗漏稿件声明的 `refs_added.bib`。修正为跟随全部
  `\bibliography{...}` 后，29/29 个 key 解析，0 缺失。arXiv 与 ACL
  Primary metadata 已核验两个原歧义条目；其他条目的逐句 claim support
  仍未审计，不能写成引用全闭合。
- T50 的 120 个 per-seed ECE 现在可从 30,000 对 archived confidence /
  correctness 按原 driver 的 rank-sorted、10-bin 定义精确重算，0 个存储
  差异；T50 ECE Comm `d=-0.0031, p=0.9864`，Cal `d=0.0699, p=0.7024`。
  这是事后重聚合，不是预注册阶段检验；逐轮 ECE 仍不存在。
- 有界本地 carrier 搜索覆盖 10,477 个可读 JSON/JSONL/CSV 文件或 archive
  member，34 个 eight-condition 命中归并为 3 个唯一内容，均为 Qwen run
  或 summary，0 个可识别 GPT-4o。因此 Finding-1 `90.8%` 与 Finding-2
  `1.06/42%/35-37%` 继续 blocked；搜索范围不等于“全盘/全网不存在”。
- Finding-1 的 11 条 `90.8` receipt 仍绑定历史 `paper_pct`；按 Qwen 条件
  均值重算 temporal share 为 `-5.15%`，summary 为
  `NO temporal fatigue`。30-seed predecessor 的 A/C/D gamma 数组逐位
  相同，继续退役。T30/T50 的 120+120 seeds、gamma/H summaries 在
  `1e-9` 内复现。
- Canonical grid 的 72 rows / 45 positive-alpha contrasts 可复算：45-cell
  未加权均值为 `-3.4819%`，per-method means 为 `-7.0%` 到 `-0.6%`，
  而单元格范围为 `-28.4083%` 到 `+33.8601%`。内部修订稿已显式区分两种
  口径，但 canonical 原稿与 stale outer/arXiv manifests 仍未改写。
- 新 `source/` 是内部 evidence-repair 版本（8 files），只修复缺失 raw
  trace 披露、CV 聚合口径和“nonsignificant ≠ equivalence”措辞。隔离
  双跑生成相同 26 页 PDF（`de132dc5...`），无 undefined citation；作者、
  license、目标与上传状态未变。编译通过不是科学就绪。
- Claim ledger：14 PASS / 0 FAIL / 6 WARN；14 claims 为 8 verified /
  6 blocked（C03/C05/C09/C10/C13/C14）。project `valid=true`、
  `ready=false`；无候选包，0 上传。
- 工厂控制面：`project_validation` 为 17/17 valid、0 ready；pytest 90、
  unittest 88、schema 28/28、全部 claim ledger 与 scoped Ruff 通过。
  measurement source binding 已覆盖带 `source#field` 的登记值；首次运行
  暴露 4 个别的 pilot 陈旧/错绑字段，修正后复跑通过。该门只验证数字与
  回执一致，不证明测量本身科学有效。
- 当前硬门：GPT-4o Finding-1 raw traces、Finding-2 raw traces、损坏的
  30-seed predecessor、outer/arXiv manifests、当前修订 hash 的独立方法/
  统计复审。arXiv 上传、作者/许可证变更仍是用户门。

## P16 Hidden Cost of Resampling archive

- Family `qf-the-hidden-cost-of-resampling-how-imbala-36f86aadfa`；project
  `qp-tmlr-tmlr-p6-60e62c7566d9`；canonical SHA-256
  `b1ea3968...`。决策 `merge_archive` / `archived`，无候选包、未上传。
- canonical 顶部明确写有 `DEPRECATED — DO NOT SUBMIT INDEPENDENTLY`；
  `MERGED_INTO_tmlr_p12_20260921.md` 再次规定不单投、不上传、不重打包、
  不改正文。独立打包工作到此停止。
- 7 个保留版本、7 个不同 hash；`arxiv/main.tex` 与 canonical 字节相同，
  不计入额外版本。
- 合并去向未闭合：`tmlr-tmlr-p12/paper/main.tex`
  （`b406b923...`）有 45 次 `N-sensitivity`，但题名、SMOTE、随机欠采样、
  isotonic、frozen embeddings、BGE-small-zh-v1.5、RF-Hybrid、
  MLP-Embed 等 study-specific 命中均为 0。只能写“存在合并意图”。
- 范围冲突：canonical 为 996 样本、6 类 synthetic style-classification；
  主快照 195431 为 1,000 样本、8 类 Newsgroups/MiniLM；N-sensitivity 为
  另一套 5-seed Newsgroups/BGE-zh。
- 标题写 Resampling，但正文只有 1 次 `resampl`、0 次 SMOTE、0 次
  undersampling，未保留实际重采样实验。
- 195431 快照重算：MLP/RF-Embed/RF-Hybrid/RF-Tabular ECE 为
  `0.1410/0.0957/0.0899/0.0606`；AUROC 为
  `0.8667/0.8778/0.8754/0.6601`；Brier 为
  `0.5752/0.4579/0.4617/0.6968`。论文印刷的 AUROC
  `0.992/0.989/0.990/0.941` 与 Brier `0.089/0.071/0.065/0.118`
  均不匹配。
- Isotonic：RF-Hybrid ECE `0.0899→0.0675`，降幅 24.86%，不是 99%；
  AUROC `0.8754→0.8375`，变化 `-0.0378`，不是 `0.037`。
- 显著性：15 对中 12 对 nominal significant，Bonferroni 后仅 10 对；
  正文 corrected `12/15` 不成立。
- N-sensitivity：RF-Embed N=200 应为 `0.150` 而非 `0.151`；
  RF-Hybrid 线性 N 相关 `-0.666`、log10(N) `-0.884`，不是 `-0.973`；
  MLP 线性 N 相关 `-0.120`，不是 `+0.078`。
- 载体：57 条全部机械 `PASS`，但 42 条存在语义错绑：33 条 quantity
  不同、3 条 model/run 错、6 条 snapshot/seed 错。57 PASS 不足以证明
  57 条 claim 有效。
- 元数据与正文冲突：anonymity 记录称匿名，canonical 作者为 Zewen Liu
  且启用 preprint；存在两个 Limitations；一边写 no sample-size sweep，
  一边有完整 N-sensitivity 表；一边称所有模型 perfect accuracy，
  快照 accuracy 实际约 0.410–0.698。
- 评审：retained review `2/8`、D veto / reject；R16 要求 Major Revision；
  无当前 hash 的独立复审。
- 验收：claim ledger 19 PASS / 0 FAIL / 12 WARN；19 claims 为 7 verified /
  12 blocked；project `valid=true`、`ready=false`；无 candidate package，
  未上传。

## P15 N-Sensitive Calibration archive

- Family `qf-n-sensitive-calibration-of-tree-ensemble-623d15100e`；project
  `qp-tmlr-resampling-calibration-632b05b06c33`；canonical SHA-256
  `4c530815...`。决策 `merge_archive` / `archived`，无候选包、未上传。
- 7 个源版本全部为不同 hash；规范稿顶部明确写有
  `DEPRECATED — DO NOT SUBMIT INDEPENDENTLY`，并称已并入 `tmlr_p12`。
  `source/MERGED_INTO_tmlr_p12_20260921.md` 再次规定不再单投、不重打包、
  不改正文。
- 合并去向未闭合：`tmlr-tmlr-p12/paper/main.tex`
  （`b406b923...`）对 N-sensitivity 题名、SMOTE、随机欠采样、resampling
  audit、frozen LLM embedding 与 synthetic style-classification 的命中均为
  0。只能写“存在合并意图”，不能写“合并已完成”。
- 范围漂移：canonical 为单一 synthetic style-classification；4 个
  arXiv-labelled 副本为 `three real text datasets`。E1 归档包含
  `20ng / ag_news / dbpedia`，与 arXiv 副本一致，与 canonical 正文不一致。
- E1 240 行，6 个 dataset/classifier 的 N=500→5000 Adaptive ECE 可重算：
  20ng RF `0.3201→0.4021`、MLP `0.1987→0.0509`；ag_news RF
  `0.3557→0.3072`、MLP `0.3608→0.0316`；dbpedia RF
  `0.5662→0.5828`、MLP `0.3906→0.0288`。
- E6 400 行；K=4 时 RF `0.2520→0.2662`、MLP `0.2032→0.0702`。这直接
  否定 abstract 的“at 4 classes, both improve modestly”。
- 载体：201 条 carrier receipt 中 159 PASS、0 FAIL、42 条完全无 verdict；
  其中 E1 26、E6 10、E8 6。印刷的 SMOTE `p=0.13`、Yeast `0.395`、
  post-hoc `-0.003` 在 `results/final_m2_m3_m5.json` 中没有命名字段。
- 评审：retained review 为 `5/10`，建议并入 `tmlr_p12`，仍保留 2 条
  Major；无当前 hash 的独立复审。
- 验收：claim ledger 15 PASS / 0 FAIL / 4 WARN；15 claims 为 11 verified /
  4 blocked；无 candidate package，未上传。

## P14 Merged Flagship F4

- Family `qf-merged-flagship-f4-verification-trust-sc-88e8c3c2ce`；project
  `qp-tmlr-f4-verification-08357385d7b0`；canonical SHA-256
  `fa583f30...`。
- 4 个源版本、4 个不同 hash；结构 15 labels、28 references、0 unresolved，
  42/42 citation 可解析。规范源按字节保留，overlay 只生成审计证据。
- 270-cell pilot、10 seeds 可精确重算：mean `0.249277...`、population SD
  `0.028931...`、CI95 `[0.245827, 0.252729]`；pooled seed block 为
  `b=44 / c=12 / n_d=56`、`chi2=17.16`、`p=2.09e-5`。
- 稿件声明 18,000 trials，归档只有 270 cells；192/144/90/40 命名的 split
  bundle 为 `0/4`；4 GPU-hours 无 per-family runtime carrier；`2700`、
  `0.686`、`0.002`、`1.47` 的 numeric carrier 均为 0。
- F4 表 4/8 行在页面精度下不能由自身 b/c 重算；2 个 RD 使用不同分母；
  Finance/Mimicry 两行复制同一 CI，且区间不包含各自点估计。
- Manifest 32 entries：19 match / 7 mismatch / 5 absent / 1 no-hash；
  carrier gate 为 30 PASS / 0 FAIL / 2 NOT_VERIFIABLE。archived pilot
  baseline BFCL/WebArena 为 `0.82/0.76`，real40 两族均为 `0.00`，正文为
  `0.95/1.05`，三套口径不能混写。
- Canonical 与 arXiv author block 不同；native ledger 仍为旧值
  `n=90, P=0.2502`；retained review 为 `1/10 reject`，当前 hash 无新复审。
- 21 条 claim 为 6 verified（含结构门）/ 15 blocked；claim ledger 为
  21 PASS / 0 FAIL / 15 WARN。处置 `blocked`，无 candidate package，
  未上传。

## Paper 2 sixth pilot

- 规范源为 `paper/main.tex`，SHA-256 `379e1632...`；`arxiv/main.tex`
  与其字节相同。
- `source/main.tex`、`.aris` 摄入副本和 legacy 目录均登记为旧版/非规范
  版本，没有覆盖原稿。
- 覆盖层只做模板清理、范围措辞修正和重复/串稿段落删除；上游字节完整保留。
- 176 条 frozen carrier receipt 全部重新解析并通过；七条 citation 均能
  解析到本地 bibitem。
- 14 条原生 claim 被重新分层：只有 11-row/66-number traceability 为
  verified；proof、held-out、estimator map、T7 与 review 仍是 candidate/blocked。
- 原生 `p=0.12` drift 陈述与 frozen `p_bootstrap=1.0` 冲突，已阻止强断言。
- 原生 T7 scope 的 8/11 描述与 frozen `n_all_constraints_satisfied=0`、
  `n_cells_tested=20` 不一致，保持阻塞。
- 3 文件候选包两次 archive hash 一致，解包隔离编译 14 页；未上传。

## Agent Behavior seventh pilot

- 规范源为 `paper/main.tex`，SHA-256 `d1eac668...`；覆盖层
  `source/main.tex` 的 SHA-256 为 `77f690d4...`，上游字节完整保留。
- 已登记 legacy、ingest drift、submission variant、source-old 和备份版本；
  覆盖层只清理模板串稿、移除虚假的形式一致性定理、收窄多智能体表述，
  并把 BDS 明确写为 whitespace-token proxy。
- 原生 `C01..C11` 已重新分层：C01/C07 verified，C02–C06 candidate，
  C08/C10/C11 blocked，C09 inconclusive；没有把 manifest 声明写成 raw
  recount。
- 8 条 frozen carrier receipt 全部通过；13 个 citation key 全部解析；
  9 文件包机械审计通过，12 页 clean-room PDF 两次 hash 一致。
- `experiments/full_run/raw/*.jsonl` 的 12 个文件全部缺失，且上游
  `evidence_manifest.json` 有 62 个 missing entry；这是公开评审的硬阻塞，
  不会伪造或重生成原始 cell。
- 候选包 `reports/package/paper35-arxiv-candidate.tar.gz` 为 9 文件、
  确定性 hash `76d6a559...`；未上传。

## Verifier Capture eighth pilot

- 规范源为 `paper/main.tex`，SHA-256 `42fe9b13...`；覆盖层
  `source/main.tex` 的 SHA-256 为 `fdfdb030...`，上游字节完整保留。
- 覆盖层删除了串入的 GPT-4o/GSM8K/MMLU/HumanEval 模板、重复的
  Reproducibility/ethics 段落、无证明的 ATV Theorem 2 和多个绝对化断言。
- 原生的“majority 在四个场景都最强”被证据否定：S1–S3 为 best/tied，
  S4 的 trust-mean 为 `0.8506`，比 majority 的 `0.8430` 高 `0.0076`。
- 4 scenarios × 7 methods × 5 seeds × 1,000 rounds 的 aggregate 全部从
  per-seed records 重算通过；1 条 carrier receipt 通过；本地 Ollama
  pilot 的 20 questions × 4 slots × 3 seeds 也从 cells 重算，七个方法均为
  `0.9167`，但仅作描述性证据。
- `ensemble_sweep.json` 的 N=10 结果是 trust-median `0.7668`，高于
  majority `0.6785`；稿件已撤回“majority 随 N 增大始终最强”的表述。
- 11 条 claim 为 7 verified / 0 candidate / 3 blocked / 1 inconclusive；
  5 文件候选包两次 archive hash 一致，解包隔离编译 15 页，archive hash
  `c0e51c1b...`；未上传。

## Calibrating the Evaluator ninth pilot

- 规范源暂存为 `evidence/upstream/main.tex`，SHA-256
  `e9487a09...`；六个源版本均为不同 hash，未覆盖任何上游字节。
- arXiv API 返回 `2606.31371v1`，标题一致，唯一作者 Zewen Liu；原始 XML、
  HTTP 响应头、查询时间和 SHA-256 均已落盘。身份存在不等于结果可复现。
- 归档驱动只实现 1,200 rounds、2,400 executor calls、1,800 evaluator calls；
  稿件印刷 2,400 / 2,400 / 3,600，分别少 1,200 rounds 与 1,800 evaluator
  calls。
- 驱动没有 length-normalized 或 symmetric-LR 对照，并将模型写成
  `deepseek-chat` / `gpt-4o`；稿件写 DeepSeek-V4-Pro / GLM5.2。
- `experiments/calibrated_ttrl.json`、20–49% gamma 与 45–67% JSD 的逐 seed
  carrier、31% 与均值置信区间 raw 均缺失。
- 当前 calibration-landscape 合并稿在 Appendix B 明确把
  `tmlr-p9/p10 calibrated-TTRL` 定位为 protocol deposit only。
- 因此 P9 处置为 `merge_archive` / `archived`，不创建独立候选包，不上传。

## Closing Calibration Landscape tenth pilot

- 规范上游 SHA-256 `8314b7b1...`；6 个源版本（5 个 packet variant 加 1 个
  source mirror）均为不同 hash，未覆盖原稿。
- 覆盖层把标题与结论收窄为“复现失败分析”，移除 `\end{document}` 之后的
  残留文本、重复实验段和仍声称 TEE 降噪/降偏置的句子。
- 15 seed 仿真 gamma 均值 0.143 / 0.719 / 0.574 可由 checkpoint 精确重算；
  CV 0.192 / 0.134 / 0.174 在四种逐 seed 定义下最近误差仍为
  0.0297 / 0.0164 / 0.0290，保持不可复算。
- real-API CG 与 CG+TEE 在 15/15 seeds 上均为 gamma_TV=0、
  gamma_VT=0、H_T=1、H_V=1；高层面 runner 的置信度解析异常会静默回退
  0.5，从而产生零更新。
- N=15 结果文件没有模型、endpoint 或 parser-success 字段；固定 parser 的
  本地 smoke 仅为 3 seeds × 10 rounds，不能替代正式复跑。
- `cg_tee_final_results.json` 的 uncalibrated/calibrated 均值
  0.991/0.602 给出 39.249% reduction，但 CG+TEE 均值 0.644 比 calibrated
  高 0.0419；39.2% 不是 CG/TEE 结果。
- 11/11 carrier 与 26/26 citation 机械解析通过；两个隔离编译目录均生成
  同一 10 页 PDF。7 文件候选包确定性 hash `e7334928...`，未上传。

## Conditional Communication eleventh pilot

- 7 个 packet variant 加 1 个 source mirror，共 8 个不同 hash；现行
  paper13 canonical `5a9b0ae4...` 保留字节不动。
- 结构审计通过：1 个 title/author/end-document，22 个唯一 label、33 个
  reference、40/40 citation key。
- 联合实验 metadata 为 4,000 calls、125 sessions、5 tasks、5 seeds；文档口径
  的平衡 ANOVA 复算为 `F_alpha=6.61`、`F_T=2.95`、`F_interaction=2.22`。
- carrier 自带的 `8.16 / 7.845 / 15.37` summary 与 sessions 不同源；精确
  reachability 判定 `SS_within=2.8975` 不可达，旧 source mirror 仍印
  `8.16 / 7.84 / 15.37`，不能单投。
- Face-1 C5 CAF 端点与 CI 在保留 JSON 中 0 命中；GPT-4o temporal
  decomposition 的 per-repetition ECE 从未归档，`+0.207 / d=4.85 / 90.8%`
  保持 blocked。
- `+0.228/+0.207/+0.021` 的讨论保留为 carrier-reported，不作为独立复算结论。
- E4 30-seed 的 TV/VT coupling reduction 为 30.765% / 29.348%；五条件
  landscape 相关为 `-0.989 / -0.916`，deepseek-v4-pro held-out n=3 的
  mean ΔECE 为 `-0.0067`。
- 评审仍为 open，critical/major 未关闭；本 pilot 处置为 `blocked`，无候选包。

## Memory Architecture twelfth pilot

- 4 个 packet variant 加 1 个 source mirror，共 5 个不同 hash；canonical
  `f926cae5...`，清理后 overlay `b2190494...`。
- 覆盖层移除了重复 Experimental Setup、无关 calibration/self-eval 串稿、
  重复 Reproducibility、错误脚本名和 `2.39` 末位错误；只保留一个 novelty
  与一个 reproducibility block。
- R1 的 90 条 per-seed records 与 9 个 paired contrasts 全部重算通过：
  canonical p=0.8 Summarization-vs-Append 为 `Δ=0.0727`、`t=3.725`、
  `p=0.0047`、`d_z=1.178`。
- v4-flash 18 cells 与 carrier `0.521 / 0.521 / 0.607 / 2.385` 对齐；
  Round-4 aggregate 记录 1,080 logs / 36 cells，flash reversal `+0.2024`，
  pro null `+0.0007`。
- Qwen authority 点估计 `0.544 vs 0.802` 可复算，但仅作为 output-length
  response；authority-bias 构念仍未验证。
- 35/35 citation、7/7 carrier tool rows、两个隔离编译目录均通过；26 页
  PDF hash 一致。10 文件候选包确定性 archive `6a2eea0b...`，未上传。

## Merged Flagship F2 thirteenth pilot

- Family `qf-merged-flagship-f2-k-generalization-sele-112d818110`；project
  `qp-tmlr-f2-theory-c2a925d103e9`；canonical SHA-256
  `cdf8485e...`。
- 覆盖层核对 3 个 packet variant 加 1 个 source mirror，共 4 个不同 hash；
  工厂 review packet 的一般 `variants_to_reconcile` 信号为 2（相对 primary
  的额外版本数），两者口径不同。规范源按字节保留，没有用修补稿替代原稿。
- 结构并非 clean：17 个唯一 label、32/32 citation 可解析，但 `alg:run` 和
  `lst:runschema` 未解析；结构门在 claim ledger 中记为 `blocked`，审计原始
  `gate_states.structure` 为 `failed`。
- `joint_2700.json` 声明 2,700 cells / 2,700 holds，实际只有 5 行、3 个
  K/gamma 条件且有重复；`analysis_2700.json` 有 6 个摘要。
- `bootstrap_2700.json` 有 2 个 point/per-seed 均值差异超过 0.005；
  `per_seed.jsonl` 与 6 条件分析摘要中 4 个不一致。
- `episodes.jsonl` 只有 180 条、2 个 gamma level，缺少 gamma=2.0。
- real-LLM 归档调用 `64+128+192=384`，稿件声明 `192/144/90/40=466`；
  real64 有 1 个失败条件与 8 个恒定 product，real128 尚余 1 batch，
  real192 只有 summary string。
- p16 缺少 `dz/d/ci/p` 字段；protocol 的 218 bytes 不包含声明阈值；
  proof 的 `0.14–0.26` 与 abstract 的 `0.35–0.56` 冲突；7 个 flagged
  values 有 0 个 executable carrier。
- 21 条 claim 为 5 verified / 16 blocked；claim ledger 为 21 PASS /
  0 FAIL / 16 WARN；review card 为 2/10 reject，当前 hash 的独立复审仍 open。
- 处置：`blocked`，无 candidate package，未上传；先重建逐 episode/逐 seed
  carrier 并修复引用和效应载体，之后才可申请新的独立评审。

## f-acceptance second native closure

- 上游基线保留在 `evidence/upstream/main.tex`，SHA-256
  `4c593778...`；覆盖层修订 `986c0a30...` 只移动 bibliography 到
  appendix 之前，没有改原目录。
- 21 条 review-response 本地审计项全部转为 passed；唯一 blocked 项是
  “独立复审绑定当前源”。
- 231 个未校正 anti-conservative cells 与 9 个连续性校正 conservative
  cells 的完整 cell tuple 交集为 0。
- 候选包 `reports/package/f-acceptance-arxiv-candidate.tar.gz` 为 6 文件、
  35,355 B，两次 archive hash 一致，解包编译 14 页。

## Verification

- pytest：89 passed、1 warning、22 subtests passed；
- unittest：87 tests OK、4 ResourceWarnings；
- schema：27 个 payload 全过；
- project validation：16/16 valid、0 ready；
- Claim Ledger：ARC 11/0/2、Paper11 20/0/0、Noise 8/0/2、F 13/0/1、
  Gemma 8/0/1、Paper2 14/0/2、Paper35 11/0/4、Paper6 11/0/4、
  P9 14/0/6、P10 16/0/5、P11 15/0/5、P12 20/0/4、P13 21/0/16、
  P14 21/0/15、P15 15/0/4、P16 19/0/12
  （PASS/FAIL/WARN）；
- scoped Ruff 与 `git diff --check` 通过。

权威回执：

- `artifacts/research-factory/v2/verification.json`
- `artifacts/research-factory/v2/pilot-status.json`
- `artifacts/research-factory/v2/package-audits/index.json`

## Next actions

1. f-acceptance：针对 `986c0a30...` 做独立 method/statistics 复审，关闭 C11；
   复审通过后只需用户确认 metadata、license 和上传授权。
2. Noise Floor：在新的 revision 中把 producer-baseline 规则收窄为可证伪的
   construct-validity audit，或补真实不相交 gold pool 正例；同时恢复或刷新
   native manifest 的源身份。
3. Gemma：恢复当前远端发布源的精确字节，再生成 LaTeX/BibTeX arXiv source；
   在源身份闭合前不得把 Markdown 发布稿当作 arXiv 输入。
4. ARC：落盘官方 scoring methodology 与精确 published source，关闭 C09/C10。
5. Paper 2：完成 Proposition 1–3 的独立 proof audit；补齐 held-out 30–40
   条件；重算或撤回 `p=0.12`；和解 T7 8/11 与 0/20；再做独立 meta-review。
6. Paper 35：恢复或取得 12 个 full-run raw JSONL 后重算 1,200 cells；
   补齐 62 个 manifest 缺失项；补 BDS tokenization/top-K/smoothing 敏感性、
   层次推断和独立 method review。
7. Paper 6：补 held-out real-trace benchmark、tau/alpha sweep 和独立
   method/statistics review；保留 S4 与原生 C02 的冲突记录，不能把
   universal negative result 或 ATV guarantee 写成已证明。
8. 按 `review-packets/top20.md` 开始人工/作者处置；机器建议与 final
   disposition 继续分列，不允许自动批量标 `arxiv-ready`。

9. P11 Conditional Communication：先恢复 Face-1 CAF 原始逐 seed 数据与
   GPT-4o per-repetition ECE 行；再重建 joint carrier summary，禁止使用
   8.16/7.845/15.37 或旧 source mirror 单投。

10. P12 Memory Architecture：补回 Round-4 的 1,080 条 raw per-seed logs，
    执行 blinded authority-uptake、来源归因、format/refusal discriminant
    audit，并把独立 review 绑定 `b2190494...`。

11. 批量处置：按 `artifacts/research-factory/v2/agent-dispositions.json`
    推进，每次选择最高优先级、无包、非 merge 的 family；所有
    `merge` family 必须先完成 canonical source 与 variant reconciliation。
12. P13 Merged Flagship F2：先修复 2 个未解析引用；重建 K=3..5 每个条件的
    per-episode 与 per-seed carrier；从原始行重算 bootstrap/analysis；恢复
    p16/p18/p21 字段级效应载体；再做当前 hash 的独立 proof/statistics review。
    在此之前保持 `blocked`，不得把 declared 2,700/18k 结果升级为实测。
13. P14 Merged Flagship F4：先恢复 18,000 trials、2,700 holds、
    192/144/90/40 split bundle 与 GPU-hour 的逐观测 carrier；重建 F4 表
    4 个不一致行的分母和 b/c；修复 manifest 的 7 mismatch/5 absent；
    和解 baseline 三套口径和作者元数据；再做当前 hash 的独立复审。
    在此之前保持 `blocked`，不得创建 candidate package。
14. P15 N-Sensitive Calibration：保持 `merge_archive`；只有作者决定复用内容时，
    才在 canonical `tmlr_p12` 内统一数据集范围、补齐 resampling carrier 与
    42 条 verdict，并对合并后的新 hash 重新评审。
15. P16 Hidden Cost of Resampling：保持 `merge_archive`；不得为 side shell
    建包。下一族改按 review queue 选择 `qf-calibration-fatigue-...-3c06d49517`
    （P1，suggested `merge`）；先完成 canonical/variant 对账与 merge marker
    核验，再决定补证、合并或 blocked。

自主接力：`research-factory` heartbeat 每 12 小时只推进一个有证据边界的
安全步骤；无有意义变化、仍受同一用户门阻断或没有可执行动作时保持安静。

No upload, external account action, paid resource use, or claim of acceptance or
publication was performed.

---

## 90 天计划阶段进度（2026-10-30）

| 阶段 | 状态 | 判据符合 |
|---|---|---|
| D1-D15 控制面 | ✅ 完成 | 131 族生产队列生成、5 pilot 固化、外置覆盖层、ledger/source-lineage 登记 |
| D16-D30 首轮人工处置 | ⏸ 未开始 | 133/133 族 final_disposition=unreviewed；人工动作 Agent 不擅自决定 |
| D31-D45 证据闭环 | ✅ 机械部分完成 | 11/17 pilot 有正文报告，全部 0 FAIL；主要缺口仅 verifier-capture tab:dz 20 个 d_z |
| D46-D60 起草闭环 | ✅ 完成 | PAPER_PLAN 5/5、章节草稿 5/5、图表实体 5/5、独立评审 5/5、citation-verification 3/3 |
| D61-D75 首批 arXiv 包 | ⚠️ 部分达成 | 机械打包 3/5（paper11/bench/f-acceptance），独立评审 5/5（达标） |
| D76-D90 批次扩产 | ⏸ 未达成 | P0=3/P1=30 未关闭（根因 D16-D30 人工处置未开始） |

### 关键结论

1. **D31-D75 的 Agent 机械部分已推进到底**：证据闭环、PAPER_PLAN、独立评审（5/5）、citation-verification、机械包评估全部完成并提交（00e65be/f64e09c/a4c8aa8/26e24e3）。
2. **剩余阻塞均需人工/用户授权**：D16-D30 人工处置（133 族 final_disposition）、arXiv 上传/作者/分类/许可证（用户门）、gemma/arc LaTeX 工具链（外部资源）、bench C02/C03 + f-acceptance C11 + arc C09（独立评审未闭合项）。
3. **非静默缺陷**：所有未达成判据均在评估报告中显式列出，无静默降级。

### 未闭合项清单（Agent 不能自行解除）

- bench C02（发表身份）+ C03（构念效度）
- f-acceptance C11（独立评审绑定源哈希）
- arc C09（官方计分法快照 + 计分器夹具）
- gemma 源身份（本地 WRITEUP vs 发布源）
- gemma/arc LaTeX 工具链（无 pandoc/pdflatex）
- 5 篇 arXiv 上传/元数据（用户门）
- 133 族人工处置（D16-D30）
