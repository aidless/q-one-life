# SUBMISSION CHECKLIST — 2026-10-25（本月两篇：F + Approval Gates R5.2）

> **⚠️ 2026-10-26 晚间事件**：AG（submit/8220836）收到 arXiv 版主 **decline** 邮件
> （标准模板：版主决定不接受提交；"benefit from additional review and revision"；
> 期刊发表并取得 DOI 后可申诉）。属 moderation 拒稿，非格式/编译问题。
> 处置约定：**不立即重投**（同内容重复提交可能升级为账号级限制）；
> 先由用户回信 moderation@arxiv.org 要求说明具体政策条款；
> 同时盯 F（submit/8283943）的 moderation 结果——存在同样被拒风险。
> F 的 TMLR 投稿线不受此事件影响。
>
> **→ 后续（2026-10-26 21:36 PDT）**：AG 已重构为独立新稿 R1
> `~/arxiv-publication/rebuild-census-20261026/`（8 页、8 条文献、单主体 97-ID census，
> 已删 §admission 与 Part I/II），**计划 11 月投**，本文件中的 R5.2 提交动作作废。
>
> **2026-10-26 16:3x PDT 已提交 arXiv，双双 on hold**：
> - **AG → submit/8220836**（标题 When Zero Does Not Mean Safe…，cs.AI 主类）
> - **F → submit/8283943**（标题 The Name Is the Contract…，cs.LG 主类）
> 两稿状态 on hold = 等版面审核（正常流程）；本月 2 篇/月限额已用完；
> 后续只等 moderation@arxiv.org 邮件，不做任何 update/delete/unsubmit。

> **2026-10-26 终审修复后更新**：F 稿按终审报告（`FINAL_REVIEW_2026-10-26.md`）修复
> 台账人口（7→14，5 promote / 9 hold / max n=12）、`luo2016flaky` 元数据、
> 摘要 118/82、+1→+3、cc 表述（disjoint set）、§8 表行序、bibliography 位置等
> 全部 BLOCKER/MAJOR/MINOR 后重编；`verify_f_v2.py` 断言同步更新，**79/79 通过**。
> 三份 main.tex 重新字节相同（`c766605c26e5b814...`），main.bib 同步（`d9c73ccb66b43d13...`）。
> 旧版本 PDF/tar 均留 `.bak-*`。
>
> **2026-10-25 决策**：10 月交付 **F** 与 **Approval Gates R5.2**。
> A（`a-obligation-tmlr`）第二标注者只有用户本人，维持**单编码**，论断上限为
> token 发生率 + 局限，不外推语义披露/沉默下界；A 移到 11 月线，本月不投。
> 本文件取代 `SUBMISSION_CHECKLIST_F_A.md`（2026-10-23 版，11 页/73 检查已过时）。

## 一、终态产物（全部实测，2026-10-26 重编）

| 论文 | 用途 | 路径（相对 `agent-verifiability/`） | 页数 | sha256（前 16 位） |
|---|---|---|---|---|
| F | **TMLR 上传**（匿名） | `manuscript/f-acceptance-tmlr/main_tmlr.pdf` | 14 | `6a5746f4c1ad3770` |
| F | **arXiv 上传包** | `manuscript/f-acceptance-arxiv.tar.gz` | 6 文件 | `df63e71007538686` |
| F | arXiv 实名参考 PDF | `manuscript/f-acceptance-arxiv/main.pdf` | 14 | `1514ff1dd2488492` |
| F | TMLR 实名参考（**勿传**） | `manuscript/f-acceptance-tmlr/main.pdf` | 14 | `bd94bfed8a6985b0` |
| AG | **arXiv 上传 PDF** | `<WORKSPACE_ROOT>/arxiv-publication/submission-ready/approval-gates-r5/Approval-Gates-R5.2.pdf` | 18 | `0ec4f010b39671e0` |
| AG | **arXiv 上传包** | `.../approval-gates-r5/Approval-Gates-R5.2-arXiv-source.tar.gz` | 9 文件 | `c851174ee9b40755` |

F 三份 `main.tex`（tmlr / arxiv / dev）字节相同：
`c766605c26e5b814ca157e9ac5d5900dde941b33dbba3c5c70dfeb21c414e58a`。
表单标题/摘要纯文本见 `manuscript/F-FORM-TEXT.md`。
F 上传清单：`manuscript/F-SUBMISSION-SHA256SUMS.txt`（6/6 OK）。
AG 校验清单：`.../approval-gates-r5/SHA256SUMS.txt`（R5.2 两件已重生成并 OK）。

## 二、已验证证据

### F

- `verify_f_v2.py --tex` 对 TMLR 与 arXiv 两变体各 **79/79 通过**（rc=0）；
  台账断言已随人口修正更新（14/14、n≤12、five promotions）。
- TMLR 匿名 PDF：`pdf_anon_check.py` **0 处不通过**，pdfauthor 显式置空，
  文本层姓名/邮箱/绝对路径 **0 命中**；首页 "Anonymous authors"。
- arXiv tar：6 文件、owner 0/0、无用户名；解到全新目录 pdflatex ×3（包内已含 `.bbl`）
  **13 页、0 error、0 undefined、0 Overfull、0 `??`**，包内 `main.tex` 与工作区逐字节相同。
- 独立评审的 1 P1 + 6 P2 + 数值口径问题已全部修入：`--scan` 单列为 reporter；
  旧表“exit codes 属于 selftest”改写为“rule 以上是 gate、以下是 reporter”；
  79 fetched / **78 classified**；行号 **304–316**；$10^{-4}$ 改为“more than three
  orders of magnitude”并列出 0.149446 / 0.152610 / 0.1555；删除 convenience
  sample 的 “floor on the defect rate” 与 “production code”；摘要补 **1/68**；
  `no-flips` 按工具区分（`acceptance_gate_audit.py` 退役、`mcnemar_audit.py` 仍 live）；
  post-repair 误差改为 **2.0e-15 (n≤200) / 2.7e-15 (n≤500)**。
  `verify_f_v2.py` 新增 5 条防回归检查（79/79）。
- 公开代码调查由 0/68 更正为 **1/68**：`Gurp-S/XEYO` 的 `mcnemar_exact`
  在 `n>500` 时静默转 `mcnemar_normal`。复判脚本与逐行证据：
  `wave2-F-acceptance/github_survey/readjudicate.py` →
  `raw/classification-readjudicated.json`（68 defs，1 反例，67 无样本量切换）。
  论文正文只出现 "1 of 68"，无 "0/68"。
- 新增 §"What the exit code means" 的两组数字已于 2026-10-25 从工作区根目录复跑：
  `evo_agent` 目标 exit 0 / `is_exact:false` / 84 flips / 10,019 cells /
  max abs error 0.15261；`paper_workflow_kb` 目标 exit 0 / 5 flips /
  0.155481。工具哈希 `ac317080ea41af8d`、`1227899ea8e2cf8a` 与正文一致。

### Approval Gates R5.2

- `Approval-Gates-R5.2.pdf` 18 页；tar 在全新目录 pdflatex+bibtex ×3：
  **18 页、0 undefined、0 Overfull、0 `??`**。
- 表单摘要 **1,894 字符**（arXiv 硬限 1,920；原 1,939 会拒绝提交，首轮删至 1,892，复核时恢复 "on its own" 限定语并将 "in both versions" 收为 "in both"，数字与结论未改），与 `src/main.tex` 的 abstract **逐字一致**（归一化空白后比对）。
- `ARXIV_METADATA.md` 的「上传文件」段已从 R5.1/16 页更正为 R5.2/18 页；
  `SHA256SUMS.txt` 已补 R5.2 两项与 `src/tables/` 五项并全部通过。
- 上传路径沿用草稿 **8220836**（替换旧 R3 文件），不新建稿件。
- 许可：**CC BY 4.0**；由用户本人在 arXiv License 步骤点击。

## 三、只能由用户完成的动作

### P0 —— arXiv（F + AG，约 20 分钟）

1. **F**：新建/进入 arXiv 投稿，上传 `manuscript/f-acceptance-arxiv.tar.gz`
   作为唯一源码包；标题、摘要从 `manuscript/F-FORM-TEXT.md` 粘贴；作者
   Zewen Liu / Independent Researcher / 17353895263@163.com；Primary **cs.LG**，
   cross-list **cs.AI**；License 建议 **CC BY 4.0**；Comments `13 pages`。
   以 arXiv 预览为准核对 **13 页**、作者名、无 `??`，再提交。
2. **AG**：进入草稿 **8220836**，删除旧 R3 文件，上传
   `Approval-Gates-R5.2.pdf` + `Approval-Gates-R5.2-arXiv-source.tar.gz`；
   按 `ARXIV_METADATA.md` 填标题/摘要/Comments；Primary **cs.AI**，
   Secondary **cs.SE**；License **CC BY 4.0**；预览核对 **18 页**后提交。
3. 两篇都记录 arXiv 回执编号与提交时间，回填 Obsidian 排产页。

### P0 —— TMLR（F，OpenReview，用户账号）

1. 新建 TMLR submission，上传 `manuscript/f-acceptance-tmlr/main_tmlr.pdf`
   （**只传匿名件**）。
2. 标题/摘要用 `F-FORM-TEXT.md`；作者只填 OpenReview profile。
3. 正文、摘要、补充材料链接**不得**出现 arXiv 编号或实名版链接。
4. 记录 OpenReview 投稿编号与时间。

### P1 —— 可选 Zenodo（暂缓）

- **不要上传** `zenodo/f-acceptance-zenodo.zip`：它仍是 0/68、73 检查、
  12 页旧版，与 2026-10-25 稿件矛盾。先重建再 mint；未重建前保持 DOI 缺省
  （论文 Data availability 已写 "deposit in preparation"）。

## 四、身份闸（上传前逐条核对）

- ✅ TMLR 只传 `f-acceptance-tmlr/main_tmlr.pdf`；❌ 同目录 `main.pdf` 是实名件。
- ✅ arXiv F 只传 `f-acceptance-arxiv.tar.gz`；❌ dev 目录 `f-acceptance/main.pdf` 是母本。
- ✅ AG 只传 `Approval-Gates-R5.2.*`；❌ 不要传 R5/R5.1，除非回退。
- ❌ 旧 10-23 F tar、旧 Zenodo zip、`submission_v5.zip` 一律不传。

## 五、复验命令（提交前可重跑）

```bash
cd "<WORKSPACE_ROOT>/F:\deepseek/agent-verifiability"
python3 wave2-F-acceptance/verify_f_v2.py --tex manuscript/f-acceptance-tmlr/main.tex
python3 wave2-F-acceptance/verify_f_v2.py --tex manuscript/f-acceptance-arxiv/main.tex
python3 ../scripts/pdf_anon_check.py manuscript/f-acceptance-tmlr/main_tmlr.pdf
cd manuscript && sha256sum -c F-SUBMISSION-SHA256SUMS.txt
cd <WORKSPACE_ROOT>/arxiv-publication/submission-ready/approval-gates-r5 && sha256sum -c SHA256SUMS.txt
```
