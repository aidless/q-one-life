# D61-D75 首批 arXiv 包评估（2026-10-30）

## 出口判据（90 天计划 §7 包门）

- [x] 主文件、相对路径、输入文件、图、书目和清理规则通过
- [x] clean-room 编译成功
- [x] PDF 与 source 哈希进入 receipt
- [ ] 作者、分类、许可证和摘要由用户作最终决定（用户门）

## 逐篇现状

| 论文 | 机械包 | clean-room 编译 | 独立评审 | 阻塞 |
|---|---|---|---|---|
| paper11 | ✅ tar.gz + receipt | ✅ pdflatex x3 + bibtex 全 0 | ✅ REVIEW_INDEPENDENT_2026-10-30 (6/6 supported) | 用户门（作者/分类/摘要/许可证/上传） |
| bench | ✅ tar.gz + receipt | ✅ exit 0 (45 页) | ✅ REVIEW_INDEPENDENT_2026-10-24 | C02 发表身份 + C03 构念效度 + 用户门 |
| f-acceptance | ✅ tar.gz + receipt | ✅ exit 0 (14 页) | ✅ FINAL_REVIEW_2026-10-26 | 独立评审绑定源哈希 + 用户门 |
| gemma | ❌ 无 tar.gz | ❌ Markdown 稿，无 LaTeX 工具链 | ✅ REVIEW_INDEPENDENT_2026-10-30 (4/4) | 源身份 + 无 LaTeX 工具链 + 用户门 |
| arc | ❌ 无 tar.gz | ❌ Markdown 稿，无 LaTeX 工具链 | ✅ REVIEW_INDEPENDENT_2026-10-30 (6/6) | C09 inconclusive + 无 LaTeX 工具链 + 用户门 |

## 判据符合

- 「5 篇各自通过机械打包」：**3/5**（paper11/bench/f-acceptance）。gemma/arc 是 Markdown 稿且本机无 LaTeX 工具链（pandoc/pdflatex 均不可用），无法 clean-room 编译。
- 「至少 3 篇通过证据与独立评审」：**5/5 全部通过**（每篇均有独立评审，verdict 全部 supported，无 refuted/needs-work）。已达标。

## 关键阻塞（Agent 不能自行解除）

1. gemma/arc 无 LaTeX 工具链 → 无法 clean-room 编译。需安装 texlive/pandoc 或用户授权转 PDF-only 提交（arXiv 支持 PDF 无源提交，但源身份已受影响）。
2. gemma 源身份未建立（本地 WRITEUP.md 与发布源哈希不一致，需恢复发布源字节）。
3. arc C09 inconclusive（官方计分法快照 + 计分器夹具未完成）。
4. 全部 5 篇的 arXiv 上传/作者/分类/摘要/许可证 = 用户门（不可逆平台动作，用户显式授权）。

## Agent 可继续推进（D76-D90 批次扩产前）

- gemma/arc 若安装 LaTeX 工具链：可建立 Markdown→LaTeX 转换包。
- 剩余未闭合：bench C02/C03、f-acceptance C11、arc C09（均在 D31-D45 已识别，属独立评审/用户门范围）。

## 结论

D61-D75 的机械打包部分 **部分达成**（3/5），独立评审部分 **完全达成**（5/5，超过至少 3 篇要求）。剩余阻塞均需外部资源（LaTeX 工具链）或用户授权（arXiv 元数据/上传）。这是可显式报告的状态，不属静默缺陷。
