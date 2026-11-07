# 10 个外部 PaperBench 任务覆盖报告

日期：2026-11-07。上游 revision：`b78dab1da774a6456b1ed9c48c9ff194ee3ff36d`。

结论：10 个选定任务的论文文本与 rubric 已在本地落地，文本 LFS 指针已按
Git LFS batch API 下载并逐文件 SHA-256 校验；其中 3 个任务有 Q-One 提交包。
**没有任何真实 PaperBench 分数**。

## 选定任务

| split | paper_id | rubric 叶子 | 文本 | Q-One 提交 |
|---|---|---:|---|---|
| dev | semantic-self-consistency | 77 | 已校验 | 有 |
| dev | self-expansion | 253 | 已校验 | 有 |
| dev | self-composing-policies | 275 | 已校验 | 有 |
| lite | fre | 437 | 已校验 | 无 |
| lite | test-time-model-adaptation | 163 | 已校验 | 无 |
| lite | mechanistic-understanding | 96 | 已校验 | 无 |
| lite | all-in-one | 174 | 已校验 | 无 |
| lite | stay-on-topic-with-classifier-free-guidance | 121 | 已校验 | 无 |
| testing | lca-on-the-line | 819 | 已校验 | 无 |
| debug | rice | 361 | 已校验 | 无 |

汇总：`coverage.json -> summary`。10/10 文本 materialised，3/10 有提交，
0/10 有真实分数。

## 静态文本共现审计

三个 `*-static-coverage.json` 只做关键词共现盘点，不是 judge。抽样已证明
`Code Execution` 类叶子也会因为 README/代码里出现同词而命中，所以：
- 不能把 `code_mentions_terms` 当通过项；
- 不能把 69/77、241/253、240/275 写成覆盖率；
- 只能说「提交文本与 rubric 有这些关键词共现」。

## 数据获取方法

对每个 `paper.md` / `addendum.md` / `judge.addendum.md` 指针：
1. 读取 `oid sha256` 与 `size`；
2. 调用 `https://github.com/openai/frontier-evals.git/info/lfs/objects/batch`；
3. 下载返回的 `href`；
4. 校验字节长度与 SHA-256 都等于指针；
5. 校验通过后才覆盖本地指针文件。

PDF 仍是 LFS 指针；本轮只补文本，不为 10 任务下载 PDF 大文件。

## 不能声称

- 没有真实 judge 分数，也没有能力评测结论。
- 3 份 Q-One 提交是按架构/机制实现的可运行参考包，不覆盖全部 rubric 叶子。
- `debug/rice` 只用于上游调试，不作为能力样本。
- 静态关键词共现不是执行、复现或判分证据。

## 下一步

1. 为剩余 7 个任务生成或手写可运行提交包。
2. 接真实 judge 前必须获得 API key 与费用授权。
3. 若只做无成本的覆盖，可继续用 DirectSubmission + dummy judge 验证归档链路，
   但仍须把结果写成「基础设施通过」，不能写成能力分数。

## 10 任务归档验证（2026-11-07 补充）

为剩余 7 个任务补了「架构/接口级最小复现」提交包，各自 `run.py` 与
`tests/test_project.py` 可运行；这些包不声称复现论文结果。

按上游允许 split 分四组执行 DirectSubmission + dummy judge：
`dev`（3）、`human`（5，等价覆盖 `lite` 的 5 个任务）、`testing`（1）、`debug`（1）。
`lite` 不是上游 CLI 允许值，调用被拒绝，已保留失败日志 `runs/pb-cov-lite.log`。

`runs/archive-summary.json` 记录 10/10 任务都有归档回执、dummy judge 输出 1.0、
0 个真实分数。该 1.0 仍只证明提交归档与容器基础设施，不是能力分数。

## 云端 10 包矩阵（2026-11-07 补充）

在已授权 AMD 实例用 `/opt/venv/bin/python` 运行统一入口契约：
每个包都提供 `run.py`、`data/sample.json` 与 `tests/`。

`cloud/matrix.log` 与 `cloud/matrix.json` 记录：

- 10/10 包 `run.py < data/sample.json` 输出 JSON；
- 10/10 包 pytest 通过，合计 48 项测试；
- 7 个架构桩各 3 项，3 个主提交各 9 项。

这证明的是**统一运行契约与短 CPU 可运行性**，不是论文复现、不是真实 judge、不是能力分数。
