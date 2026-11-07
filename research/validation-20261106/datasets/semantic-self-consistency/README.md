# semantic-self-consistency 数据清单

日期：2026-11-07。论文附录 L 指定：AQuA-RAT test 254、StrategyQA test 687、
SVAMP train+test 1000。已用下列公开来源实测并逐文件 SHA-256 校验。

| id | 文件 | 来源 | 行数 | 字节 | SHA-256 | 授权/边界 |
|---|---|---|---:|---:|---|---|
| aqua_test | `aqua_test.jsonl` | google-deepmind/AQuA `test.json` | 254 | 130192 | `de41581881ef95c5588c44ddc701c77fd480839241dd422a0d181262af24520c` | 上游公开仓库，再分发前复核许可 |
| svamp | `svamp.json` | arkilpatel/SVAMP `SVAMP.json` | 1000 | 339970 | `5be77703a6d891ae476d7c082787ad361392aa02453b132516cdd5f4e7934e3e` | 上游公开仓库，再分发前复核许可 |
| strategyqa_test | `strategyqa_test.json` | ChilleD/StrategyQA `test.json` | 687 | 176993 | `6da41445f044a7abde29f987d3311757cd0c33e759ea6f37fa100917bf0a82b0` | MIT |
| strategyqa_train | `strategyqa_train.json` | ChilleD/StrategyQA `train.json` | 1603 | 413408 | `cba352f7b7cbe3688b6847ec55f8035c9bccd5cbcc183e8e0ddd0a79ccbbc404` | MIT |

## 恢复

```bash
python3 research/validation-20261106/datasets/semantic-self-consistency/fetch_datasets.py
```

脚本会把数据写到 `raw/`，重建 `raw/manifest.json`；行数或哈希不符即失败。
`raw/` 不入 git，仓库只保留下载命令、来源、行数、哈希和授权边界。

## 校验状态

`download-checks.json` 是本轮实测回执：3 个目标评测规模与论文附录一致。
StrategyQA train 仅作为额外上下文下载，不计入论文指定的 687 test 样本。

## 边界

- 这些是公开来源，不是论文作者打包的数据；与论文实际使用的预处理是否逐字节相同未证明。
- 没有下载或运行任何模型权重；没有发起付费模型调用。
- 数据集下载本身不等于复现论文结果，也不产生 PaperBench 分数。
