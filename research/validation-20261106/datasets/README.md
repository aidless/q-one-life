# AI Researcher 数据集先导包

本目录记录 2026-11-06 的公开数据集核实与先导下载。入口是 `manifest.json`；
原始证据在 `raw/`，可消费的派生文件在 `processed/`。`raw/` 不入 Git。

## 给评分接口的入口

PeerRead 论文级配对索引：

`processed/peerread/paper_review_pairs.jsonl`

每行是一篇论文。关键字段：

- `paper_id`、`venue`、`split`、`venue_decision`
- `paper_path`、`paper_sha256`
- `human_review_count`、`human_reviews`
- 每个 review 的 `recommendation`、`reviewer_confidence`、`date`
- `submission_version_status`

逐条 review 的扁平索引：

`processed/peerread/reviews.jsonl`

`recommendation` 是 ICLR 2017 官方 1–10 整数推荐分；`venue_decision`
只用于分层抽样，不得作为评分标签。标题/摘要没有作为完整稿件使用。

## 给轨迹标签接口的入口

`processed/ridar/paired_trajectories.jsonl`

RIV-Gold 的全部 60 条人工标注已保存；先导包下载并核验了其中 2 条完整
轨迹。每行包含 `trace_path`、`trace_sha256`、`records`、`behaviors` 和
`annotation_line_one_based`。证据位置为 `trace.jsonl` 的 1-based 行号。

## 其他先导件

- `raw/paperbench/materialized/paper.md`：PaperBench dev 任务正文，LFS OID 已核验。
- `raw/paperbench/project/paperbench/data/papers/semantic-self-consistency/rubric.json`：
  100 个 rubric 节点，其中 77 个叶子要求。
- `../pilot-data/manifest.json`：用户导出的 sklearn 1.9.1 三套 feature/label；
  本包只回验哈希和行列数，没有训练或重新下载。

## 复验

```bash
cd /home/liuzewen/qone-life-work
python3 research/validation-20261106/datasets/build_manifest.py verify
```

`verify` 会复算所有 `raw/` 文件大小与 SHA-256、检查 32 MiB 总上限，并确认
`manifest.json`/`processed/` 能由原始证据和本地导出重建。

## 禁止用法

- 不把 `venue_decision` 当 review score。
- 不把按论文切分后的同篇多评审当独立论文。
- 不把 PeerRead 的解析 PDF 当作已证实与投稿原稿一致。
- 不把 PaperBench 任务包解析成功写成端到端复现分数。
- 不把 sklearn 三套公开数据的分数写成新颖科学发现。
