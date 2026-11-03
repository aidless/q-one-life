# 两稿终审报告（2026-10-26）

审稿对象：

| 稿 | 投递目标 | PDF | 源 |
|---|---|---|---|
| **F** | TMLR（主）+ arXiv（备） | `agent-verifiability/manuscript/f-acceptance-tmlr/main_tmlr.pdf`（473 441 B，13 页） | `.../main.tex`（54 050 B，966 行）+ `main.bib` |
| **AG** | arXiv，cs.AI primary / cs.SE secondary | `<WORKSPACE_ROOT>/arxiv-publication/submission-ready/approval-gates-r5/Approval-Gates-R5.2.pdf`（338 862 B，18 页） | `.../src/main.tex`（49 259 B，588 行）+ `src/main.bib` |

审稿方式：只读。凡标「我重算」的数值均由独立脚本产出（以 `scipy.stats.binomtest` 双侧精确为参照，不复用稿件代码），出处见对应段落。

---

## 0. 一句话结论

**AG 稿可投。F 稿还不能投：有一处 BLOCKER 需要重跑。**

F 稿的台账复核（§10、摘要、§1 都引用了它）跑在 **7 行**上，而这 7 行是 3 条冒烟记录 + E1–E4 拼出来的；真实台账有 **E1–E14 共 14 个门禁裁决（5 promote / 9 hold，最大不一致数 n=12）**。结论（都在精确分支内，14/14 一致）不受影响，但数字全变，且摘要要跟着改。

除此之外，F 稿还有 5 个 MAJOR 与 7 个 MINOR，全部是一天内能改完的编辑级问题。

---

## 1. 两稿共同的合规结果

| 检查 | F | AG |
|---|---|---|
| `research_audit`（页数/摘要位置/空页/未引用图表/元数据） | **pass**，0 error / 0 warning | **pass**，0 error / 0 warning |
| 正文页数 | 13 | 18 |
| PDF 属性身份泄漏 | 无 | 无 |
| 引文真实性 | 17 条；1 条元数据错（见 §2.7），其余可查的都真 | 35 条，32 个 arXiv eprint 相似度全部 1.00 |
| 数字可复算 | 除台账人口外全部复现（见 §2.2） | 算术逐项手算吻合 |

---

## 2. F 稿（The Name Is the Contract）

### 2.1 匿名性 —— 干净

- PDF 首页明写 `Under review as submission to TMLR / Anonymous authors / Paper under double-blind review`。
- `pdftotext` 全文搜 `Zewen` / `Independent Researcher` / `17353895263` / `@163.com`：零命中。
- 正文无自引 arXiv 号（文中出现的 arXiv ID 全在参考文献里，属他人工作）。
- 源码侧写法正确：`main.tex:12` 是 `\hypersetup{pdfauthor={\ifdefined\TMLRSUBMISSION\else Zewen Liu\fi}}`，`main.tex:25-29` 是条件 author 块；`main_tmlr.tex` 只是 40 字节的 `\def\TMLRSUBMISSION{1}\input{main.tex}`。preprint 件 `main.pdf` 印作者是设计如此，不构成泄漏。

### 2.2 数字 —— 我重算，逐项吻合

| 量 | 稿件值 | 我的重算 | 结论 |
|---|---|---|---|
| 格子总数 | 62 819 | 62 819 | ✓ |
| gate 会 promote 的格子 | 55 469 | **55 469** | ✓ |
| 参照会 promote 的格子 | （未单列） | 55 238 | 差值恰为 231，自洽 |
| 未校正：反保守 / 保守 | 231 / 0 | **231 / 0** | ✓ |
| 连续性校正 | 0 / 9 | **0 / 9** | ✓ |
| mid-p | 221 / 0 | **221 / 0** | ✓ |
| `p_code > p_exact` 且 `p_exact<.05` | 41 076 | **41 076** | ✓ |
| 其中 code p 最大值 | 5.3×10⁻⁵ | **5.312128e-05** | ✓ |
| 最大绝对误差 | 0.152610 @(14,13) | 0.152610 | ✓ |
| 最大比值 | 1.525 @(19,8) | 1.525 | ✓ |
| 断点样例 (18,8),n=26 | 0.049860 / 0.075519 / 1.51× | 0.049860204 / 0.075518698 / 1.5146 | ✓ |
| 精确参照 = 1.0 的格子 | （未提） | **475** | 见 §2.9 |

另外：我的尾部定义与 `scipy.stats.binomtest` 在全部 62 819 格上分歧 0 格，所以「level-matched exact reference」站得住。稿件自带 `verify_f_v2.py --tex main.tex` 对 TMLR 变体也是 **79 checks passed, 0 failed**。

**有一处需要说明**：我另派的一名审稿人报 `41 076` 应为 `8 791`。我用同一参照独立重算，得 **41 076**，且 code p 最大值 `5.312128e-05` 与稿件里那句「the largest code p among them is 5.3×10⁻⁵」逐位相符 —— 两个独立量同时命中，`41 076` 是对的，那条意见不成立。同一脚本里 `8 791` 复现不出来。

### 2.3 ⛔ BLOCKER：台账复核跑错了样本

**稿件（§10，摘要与 §1 也重复了它）**：

> The seven entries of the audited system's evolution ledger (`EVOLUTION_LEDGER.md`…) were re-evaluated…: all seven recorded verdicts agree (**three promotions, four holds**; every entry sits at **n≤8**, inside the exact branch)

**实际 `evo_agent/EVOLUTION_LEDGER.md`（134 行，mtime 2026-09-13 20:35，早于 2026-10-17 的审计，即审计当时就是这份）**：

| 条目 | 裁决 | 不一致数 n |
|---|---|---|
| E1 / E2 / E4 | hold | 小 |
| **E3** | **promote** | 8 |
| E5 / E6 / E7 | hold | 小 |
| **E8** | **promote** | **12（b=0, c=12, p=0.0005）** |
| E9 / E10 / E11 | hold | — |
| **E12** | **promote** | 11（b=0, c=11, p=0.000977） |
| **E13** | **promote** | 8（b=0, c=8, p=0.0078） |
| **E14** | **promote** | 7（b=0, c=7, p=0.0156） |

合计 **14 个门禁裁决：5 promote / 9 hold，最大 n = 12**。

**「7 行」从哪来**：`agent-verifiability/wave2-F-acceptance/revision_stats.json` 的 `ledger_rejudgment` = `{"entries": 7, "agree": 7, "max_n": 8, "promotions_recorded": 3}`，其 `detail` 数组前两条就是 `SMOKE1#1`、`SMOKE1#2`。也就是说这 7 行 = **3 条冒烟记录 + E1–E4**。台账自己在第 128 行写着「冒烟记录（非实验，不计入门禁统计）」，第 3–4 行的记账规则也明说「冒烟自检……**不计入门禁统计**」。

**影响面**：摘要（"the system's seven-entry promotion ledger shows no recorded decision actually flips"）、§1 贡献 5、§10 正文、以及 §10 修复记录段的 "7/7" —— 全部要改。

**好消息：结论不被推翻**。最大不一致数 n=12 < 25，14 条**全部落在精确分支内**，所以「所有记录裁决与精确参照一致」这句仍然成立，只是分母从 7 变 14、promote 从 3 变 5、max_n 从 8 变 12。

**改法**：把 `revision_stats.py` 的台账复核改成遍历 E1–E14、跳过「冒烟记录」区，然后全稿统一为「fourteen gate verdicts: five promotions, nine holds; max discordant n=12, all inside the exact branch; 14/14 agree」。

### 2.4 ⚠️ MAJOR：摘要把 118 说成 paired-binomial

摘要：「A workspace-wide classifier finds **118 name-matched paired-binomial** function entries」。

正文自己拆得很清楚：118 = 60 exact-only + 48 unknown + 7 approx-only + 3 hybrid，而 §4 写「The remaining 36 are not p-value gates at all: 21 power/n/OR calculators, 12 test or selftest assertions, and 3 nested closures」。118 − 36 = **82** 才是真正的 paired-binomial 检验。

改法：`118 name-matched function entries, 82 of them paired-binomial tests`。

### 2.5 ⚠️ MAJOR：同一件事两个增量（+1 vs +3）

- §4：「a re-run delta of **+1** caused by our own artifact archive」
- 附录 A：「the live `--workspace-scan` today finds **121** implementations, not 118 — the three additional hits are all archival copies」

118 + 3 = 121，所以增量是 **+3**，§4 的 +1 与之矛盾。

改法：把 §4 的「+1」改成「+3」，与附录对齐。

### 2.6 ⚠️ MAJOR：§8 的框架句与自己的表格打架

§8 表后写：「The rows above the rule are **gates**… The rows below it are **reporters**」。

但表里 `\code{mcnemar\_audit.py} \code{--scan}` 这行标注为「*reporter*: exit 0 after printing the scan JSON; no verdict-based non-zero exit」，位置在第一条 `\midrule` **之上**，夹在两个 gate 行之间。

这一节存在的意义正是阻止「gate / reporter」混用，所以这处自相矛盾值得改。

改法：把 `--scan` 那行移到 `\midrule` 以下。

### 2.7 ⚠️ MAJOR：连续性校正那 9 格与 231 格是不相交的两批

摘要：「adding the one-line continuity correction **reverses all 231 flips into 9 conservative ones**」。

我重算：cc 保守格 9 个，与未校正的 231 个反保守格的**交集 = 0**。也就是「reverses」不成立 —— 231 格消失了，另外 9 格变成了反方向，是两批不同的格子（cc 的 p 逐点大于未校正的 p，所以它不可能把某一格从「反保守」翻成「保守」，它只能把全部格子往保守方向推，其中 9 格越过了 α 线）。

改法：`replaces the 231 promotion-side flips with 9 of the opposite sign (a disjoint set)`。

### 2.8 ⚠️ MAJOR：附录读起来像有公开存档，其实没有

附录 A 一边写「archival copies of code the program itself produced (the auditor inside the **Zenodo package**…)」，一边写「no external archive had been minted when this draft was compiled」。

实际状态：`agent-verifiability/zenodo/f-acceptance-zenodo.zip`（511 266 B，2026-10-22 06:55）**在本地存在，但没有 DOI、没有发布**。而附录里的复现命令全部是 workspace 内相对路径（`../evo_agent/...`、`wave2-F-acceptance/...`），任何外部读者都执行不了。

改法（二选一）：真发布 Zenodo 并引 DOI；或明写「本稿的数值只能由文中公式与附录命令在作者工作区内重算复现，暂无公开存档」。后者更诚实，而且这两条路里至少有一条必须选，因为 TMLR 对可复现性有明确期待。

### 2.9 MINOR 清单（7 条）

| # | 位置 | 问题 | 改法 |
|---|---|---|---|
| 1 | §3 头号数字 | 0.152610 落在 (b,c)=(14,13)、n=27 的单数格，此处**精确双侧 p 恰好封顶在 1.0**（我验了，`p_exact = 1.0000000000`），所以这个「最大误差」有一半是定义性的；§6 对 chi2 的 0.155481 做了同类分解，对自己这个没做 | 加一句：0.1526 @(14,13) 处参照封顶 1.0；**不封顶的最大误差是 0.150132 @(14,12)**（这个数我也重算过，一致） |
| 2 | §10 | 「(`EVOLUTION_LEDGER.md`; full path in App. A)」，但附录 A 全篇没出现过这个文件名（全文仅 `main.tex:776` 一处） | 把路径直接写在正文：`evo_agent/EVOLUTION_LEDGER.md` |
| 3 | §3, `main.tex:214-217` | 「all 231 flips point the same way」连续两句重复 | 删第二处 |
| 4 | §3 定向论证 | 「docstring 的 b 是 old-wins、调用点传 (old_wins,new_wins)、门是 `new_wins > old_wins` 严格大于」这条链是断言，没给证据 | 补三行代码引用，或一句话说明 |
| 5 | §3 平局 | 全区域有 **475 个格子精确 p 恰好 = 1.0**（b=c 及 |b−c|=1），这些格子永远不可能 promote，稿中从未提及 | 加一句平局说明 |
| 6 | `main.bib:47-53` | `luo2016flaky` 元数据错（详见下方） | 替换 |
| 7 | 排版 | `\appendix` 在 `main.tex:880`，而 `\bibliographystyle`/`\bibliography` 在 963-964 行 → **References 印在附录之后**（p13 在 p12 后） | 把 bibliography 移到 `\appendix` 之前 |

**关于第 6 条（唯一的一处引文缺陷）**：

| 字段 | 稿中写 | Crossref `10.1145/2635868.2635920` 权威记录 |
|---|---|---|
| title | Large-scale analysis of flaky tests in unit testing frameworks | **An empirical analysis of flaky tests** |
| 会议 | OOPSLA（31st ECOOP） | **22nd ACM SIGSOFT International Symposium on Foundations of Software Engineering（FSE）** |
| 年份 | 2016 | **2014**（2014-11-11） |
| 页码 | 145–166 | **643–653** |
| 作者 | Luo, Hariri, Eloussi, Marinov | 同（四人相符） |

作者四人相符，说明是真实论文的元数据被写坏，不是捏造。**引用位置 `main.tex:750-751` 的用法是对的**（该文确实是讲 CI 里 flaky/retried 测试的），所以只改 bib，正文不动。

建议替换：

```bibtex
@inproceedings{luo2016flaky,
  author    = {Luo, Qingzhou and Hariri, Farah and Eloussi, Lamyaa and Marinov, Darko},
  title     = {An Empirical Analysis of Flaky Tests},
  booktitle = {Proceedings of the 22nd ACM SIGSOFT International Symposium on
               Foundations of Software Engineering (FSE)},
  year      = {2014},
  pages     = {643--653},
  doi       = {10.1145/2635868.2635920}
}
```

### 2.10 建议改：10 张表全部无 caption、无编号

全稿 `\begin{tabular}` 共 **10 处**（`main.tex` 第 167、200、259、290、366、382、526、617、704、853 行），全部是 `\begin{center}\begin{tabular}` 的内联块，`\caption` 出现次数为 **0**。

这 10 处都是实义数据表：三层契约 / 区域统计 / 三变体对比 / 断点 p 值对照 / 118 实现分类 / 3 hybrid 动态结果 / 7 个动态目标 / selftest 注入清单 / 两工具状态 / 结论四步 recipe。

审稿人无法用「Table 3」指代任何一张表；每张表的语义必须回读上下散文。TMLR 无硬性页数上限，加 caption 的版面代价我没有编译验证过。

如果决定改，第 617、704 两张（`p{7.2cm}` / `p{8.6cm}` 的两列说明表）其实是列表而非表格，转 `itemize` 反而更省版面。

### 2.11 关于「两个副本」vs「三个 hybrid」

摘要说「two copies of one function」，§4 表格却列 3 行 hybrid。这**不是矛盾** —— `main.tex:396` 已明确写「surfaced exactly three, two of which are real. (The third is the verbatim transcription the audit itself carries)」。表格分类 60+48+7+3=118 也自洽。这一条我确认不需要改。

### 2.12 标题

「**Every Flip Favors Promotion**」是全稿最强断言，而摘要第 4 句、§f01、贡献 1 立刻把它限定为「relative to *that* reference」，并主动给出反证（单侧 α=0.05 参照下是 928 保守、0 反保守）。限定词出现在标题后第一屏，不是藏在脚注里，处理是对的。若审稿人只看标题就下判断，这是最可能被误解的点，但不必改。

---

## 3. AG 稿（When Zero Does Not Mean Safe）

### 3.1 引文 —— 32/35 直接验号，剩下 3 条我逐一确认存在

`reference_checker` 报 7 条 `not_found`。我全部手工复核，没有一条是假的：

| key | checker 结论 | 我的复核 |
|---|---|---|
| `awsbench2024` | not_found | GitHub `aws-samples/multiagent-collab-scenario-benchmark` 存在（19 stars，created 2024-11-06） |
| `microsoft2026actionbound` | not_found | `microsoft/agent-governance-toolkit` 存在（6471 stars）；钉住的 commit `47abed7446d47e74cfa76d01a5913bb873ffcad9` 下 `docs/adr/0030-action-bound-approval-protocol.md` 存在，15 610 字节，正文确认为「ADR 0030: Use an action-bound, fail-closed approval protocol / Status: accepted / Date: 2026-06-11」 |
| `rakazo2026` | not_found | GitHub `elie222/rakazo` 存在（5852 stars，created 2026-08-13） |
| `gao2026benchmarkscores` | not_found | arXiv 2605.10448，标题吻合 |
| `zhu2026harness` | not_found | bib key 实为 `zhu2026harnesssec`，arXiv 2610.07639 吻合 |
| `yang2026intentexec` | not_found | arXiv 2610.04375 吻合 |
| `li2026exactlyonce` | not_found | arXiv 2609.29095 吻合 |
| `bellibatlu2026contracts` | not_found | arXiv 2609.37315 吻合 |

其余 27 条 arXiv eprint 直接验号，相似度全部 1.00。

### 3.2 元数据 —— 逐字节一致

`ARXIV_METADATA.md` 的 Abstract 与 `src/main.tex` 的 abstract：完全相同，**1 894 字符**，与文件自己声明的「1,894 字符」吻合。这种一致度通常说明元数据是脚本从源文件生成的。

### 3.3 准入算术 —— 逐项手算，全对

§sec:admission 是本稿最硬的可证伪部分（闭式、不需数据）。我全部独立重算：

| 声明 | 稿件 | 我的计算 |
|---|---|---|
| `2ln(KT/δ)`，K=5,T=10,δ=0.05 | 13.82 | 13.8155 ✓ |
| m=89 → 最小可认证增益 | 39.4 pp | 39.40 ✓ |
| m=200 | 26.3 pp | 26.28 ✓ |
| m=500 | 16.6 pp | 16.62 ✓ |
| m=2 000 | 8.3 pp | 8.31 ✓ |
| m=10 000 | 3.7 pp | 3.72 ✓ |
| +7.3 pp 需要任务数 | 2 593 | 2 592.5→2 593 ✓ |
| +2 pp 需要任务数 | 34 539 | 34 538.75→34 539 ✓ |
| 2η=4 pp、增益 7.3 pp | 12 687 | 12 686.4→12 687 ✓ |
| +0.4 pp | 863 470 | 863 469→863 470 ✓ |
| T=50 时 `2ln(KT/δ)` | 17.03，缩放 1.11 | 17.034，√(17.03/13.82)=1.110 ✓ |
| m=100、10 pp | 1 382 | 1 381.6→1 382 ✓ |

可执行检查那行也对：`tmaudit admission --gain 7.3 --tasks 89` → `[NOT CERTIFIED] gain=+7.30pp upper=+32.10pp`，而 −7.3 + 39.4 = **+32.1** ✓。

### 3.4 计数自洽

- **540 cells**：6 个 guard × 每 guard 90 cells；表格逐行 9+9+18+18+18+9+9 = **90** ✓
- **388 scripted executions**：97 IDs × 4 pipelines = **388** ✓
- 摘要「5 passes in 1.2.2 / 4 in 1.2.1，4 stable，1 only in 1.2.2」与结论「two of the five request new transactions，the other three have unimplemented or underspecified scoring contracts」相加 2+3=5 ✓

### 3.5 ⚠️ 建议改：一处数值与算式差 5.7%

`src/main.tex:448-449`：

> its own largest reported effects sit near **18** pp, which at m=100 still requires **404** tasks

`404` 是从 **18.49 pp** 反解出来的（13.8155 / 0.185² = 403.66）。而 `admission-census/claims.json` 记的是 `"gain_pp": 18.5`，`CENSUS.md` 第 31 行写「+18.50 pp | 100 | 404」。

也就是：**账本是 18.5，正文写「near 18」，但 404 是按 18.5 算的。** 审稿人若拿 18.0 复算会得 427，差 5.7%。

改法：把 `near 18 pp` 改成 `near 18.5 pp` —— 与账本、与 404 三者对齐。改后重编 `Approval-Gates-R5.2.pdf` 并重打 `Approval-Gates-R5.2-arXiv-source.tar.gz`（arXiv 收 tar.gz，PDF 是预览件，两者必须同源）。

### 3.6 我认可的优点

- 全文没有一处把「构造审计」说成「自然失败率」；Limitations 七条把署名案例、契约、并发机制、准入算术的继承、工具本身、外部效度都钉住了。
- 引言明写 `We do not claim a new defense`，并主动交代 action binding 是前人工作、bound 组件是 baseline。
- 有 `Broader impact` 与 `Disclosure of generative AI use` 独立章节。
- 「对偶列重复是因为结果本身，不是转录错误」这种主动堵审稿人误会的写法，很少见。

---

## 4. 改动清单

### F 稿（按优先级）

| 优先级 | 位置 | 动作 |
|---|---|---|
| **BLOCKER** | `wave2-F-acceptance/revision_stats.py` + 全稿 | 台账复核改为 E1–E14（跳过冒烟区），重跑；全稿统一为 14 个裁决 / 5 promote / 9 hold / max n=12 / 14-14 一致；改摘要、§1 贡献 5、§10、修复记录的「7/7」 |
| MAJOR | 摘要 | 「118 name-matched **paired-binomial**」→「118 name-matched function entries, **82** of them paired-binomial tests」 |
| MAJOR | §4 | 「delta of **+1**」→「**+3**」，与附录 A 的 121 对齐 |
| MAJOR | §8 表格 | 把 `mcnemar_audit.py --scan` 行移到 `\midrule` 以下 |
| MAJOR | 摘要 | 「reverses all 231 flips into 9 conservative ones」→「replaces the 231 with 9 of the opposite sign (a disjoint set)」 |
| MAJOR | 附录 A / 数据可用性 | 发布 Zenodo 引 DOI，或明写「只能在工作区内按文中公式重算」 |
| MINOR | §3 | 补一句 0.1526 @(14,13) 处参照封顶 1.0；不封顶的最大误差 0.150132 @(14,12) |
| MINOR | §10 | 把 `evo_agent/EVOLUTION_LEDGER.md` 路径写在正文 |
| MINOR | `main.tex:214-217` | 删重复的「all 231 flips point the same way」 |
| MINOR | §3 | 补定向三行代码，或一句话说明平局（475 格精确 p=1.0 永不 promote） |
| MINOR | `main.bib:47-53` | 换成 §2.9 的 bib 条目 |
| MINOR | 排版 | bibliography 移到 `\appendix` 之前 |

改完**必须重编 `main_tmlr.pdf`**（PDF 里嵌了参考文献与数字，只改源不改 PDF 等于没改），并更新验收记录里的 sha256。

### AG 稿

| 位置 | 动作 |
|---|---|
| `src/main.tex:448` | `near $18$\,pp` → `near $18.5$\,pp`；重编 PDF、重打 tar.gz |

---

## 5. 我不代劳的部分

- **不替你改稿**：本次任务定位为只读审稿。改稿会污染 `main_tmlr.pdf` 的 sha256，而该值已被验收记录引用（`ab04cd0f...`）。要改我再来一次，会同时更新验收记录。
- **不替你投**：arXiv 两篇 + TMLR OpenReview 需要你的账号与点击。
- **两份 PDF 只做了程序化审计与文本级阅读，没做像素级视觉检查**。两稿 `\includegraphics` 均为 0（AG 的图全是 TikZ 矢量、表全是 LaTeX 原生），所以位图失真、DPI、色彩空间这类风险不存在；剩下的是矢量图的语义可读性，需要时可逐张过 `modlens_read_image`。

---

## 6. 环境副产物（供下次参考）

- arXiv API（`export.arxiv.org/api/query`）与 `web_fetch arxiv.org` 在 TUN 代理下全废（前者返回空，后者报 `URL hostname "arxiv.org" resolves to a non-public IP address`）。可用替代：`curl -A 'Mozilla/5.0' https://arxiv.org/abs/<id>` 抓 `citation_title` meta 标签。
- `domain_search(engine=arxiv)` 会 429。
- 稿件自带的 `verify_f_v2.py` 默认跑的是 `f-acceptance/main.tex`；核验 TMLR 变体必须显式传 `--tex`。
- `revision_stats.json` 有两份副本（`wave2-F-acceptance/` 与 `zenodo-pkg/data/`），改一处必须同步另一处，否则 Zenodo 包与正文对不上。
