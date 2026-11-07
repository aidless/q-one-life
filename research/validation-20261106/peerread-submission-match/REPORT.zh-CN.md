# PeerRead 送审版本对齐核验

日期：2026-11-07。结论：**23/24 篇正文与 PeerRead 仓库 `parsed_pdfs` 完全一致；
1 篇仅邮箱被脱敏。先前的“解析版本未匹配”限制可以收窄。**

## 方法

- 原始解析：`datasets/raw/peerread/data/iclr_2017/{train,dev,test}/parsed_pdfs/*.json`
- 先导解析：`datasets/processed/peerread/papers/*.json`
- 比较字段：标题、作者、章节 heading + 正文拼接的 SHA-256

## 结果

| 项 | 值 |
|---|---:|
| 先导论文 | 24 |
| 原始 `parsed_pdfs` 可用 | 40（仓库固定 revision 内全部解析文件） |
| 24 篇全部能匹配到原始解析 | 24 |
| 正文 SHA-256 一致 | **23** |
| 标题一致 | 24 |

## 唯一差异：306

- 原始与先导的章节数和 heading 完全相同。
- 唯一差异在 Introduction：先导版把作者邮箱替换为 `[REDACTED_EMAIL]`，
  原始版保留邮箱占位符 `{{EMAIL_...}}`。
- 这不是内容差异，而是处理管线在派生文件里做的脱敏。

## 对评审校准的意义

1. 之前 `submission_version_status=unknown` 的主要原因（无法证明解析版本是
   送审版）现在可以收窄：**24 篇全部与仓库固定 revision 的 `parsed_pdfs`
   匹配，23 篇逐字节一致，1 篇只差脱敏。**
2. 这仍不是“原投稿 PDF 与 OpenReview 活体”的最终证明，但比“解析版未知”
   强得多。
3. 因此 PeerRead 外部检查可以从“探索级”提升为“固定仓库解析级”，但还不能
   写成“无偏评审校准”。

## 残余限制

- `parsed_pdfs` 是 PeerRead 仓库自带的解析结果，不是我们重新从 PDF 抽取；
  我们依赖仓库的解析质量。
- 306 的邮箱脱敏说明先导文件经过了后处理，不能保证所有字段都未经改动。
- 没有 OpenReview 活体 schema 验证，评分尺度仍以官方论文为准。

## 文件

- `match.json`（24 篇逐篇匹配明细）
- `REPORT.zh-CN.md`（本报告）
