# mechanistic-understanding Jigsaw 数据清单

来源：[thesofakillers/jigsaw-toxic-comment-classification-challenge](https://huggingface.co/datasets/thesofakillers/jigsaw-toxic-comment-classification-challenge)
上的 `train.csv`。PaperBench 该任务的 `addendum.md` 明确要求使用这个公开镜像，
不要走 Kaggle 托管版本。

## 下载命令

```bash
curl -L -C - --max-time 180 \
  'https://huggingface.co/datasets/thesofakillers/jigsaw-toxic-comment-classification-challenge/resolve/main/train.csv' \
  -o train.csv
```

网络单次长连接经常在 3 分钟被切断，允许重复 `-C -` 续传。文件大小
68,802,655 字节（Hugging Face `x-linked-size`）。数据本体不入 git，
只保留下载命令、来源和校验值；提交包里的 `data/jigsaw_train.csv` 为运行时软链/副本。

## 已验证

- 本机 2026-11-07 实测：68,802,655 字节，
  SHA-256 `bd4084611bd27c939ba98e5e63bc3e5a2c1a4e99477dcba46c829e4c986c429d`。
- `train.csv` 共 159,571 条非空评论；确定性 90:10 切成 143,614 / 15,957。
- TF-IDF + `LogisticRegression` 验证准确率 0.9595（14.25 秒，CPU，本机），
  回执见 `full-slice.json`。该数不是论文的 GPT-2 残差流探针结果。

## 授权与边界

- 这是 Jigsaw Toxic Comment Classification Challenge 的公开镜像；只用于 PaperBench
  复现研究，不用于训练发布模型或生成毒性内容。
- 不下载 `test.csv` / `test_labels.csv`，当前切片只需要带标签的 `train.csv`。
- 论文剩余结果（GPT-2 残差流特征、DPO、SVD 毒性向量、约 94% 验证准确率）
  不在本切片内，不声称已复现。
