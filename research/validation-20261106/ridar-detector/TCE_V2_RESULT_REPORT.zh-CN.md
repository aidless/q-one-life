# TCE v2 检测器结果

日期：2026-11-07。结论：**开发集 precision 仍低于冻结的 0.5 停线，规则形态
仍不可用；不进入留出集作为通过。**

## 冻结协议（v2）

- 切分 SHA-256：`aa569ddd2ce4456f8b0a123af47645d275aadd4ff2fc5b36a61bf7811e8a753d`
- 规则 SHA-256：`a9be42edc30e74faff2a5838bc26c0d36990047985872984e2019de0a3a98384`
- 目标：`exploit_test_cases`；评估单位：act；切分单位：轨迹
- 留出 TCE 正例：14 acts / 10 条轨迹，满足下限
- 停线：开发集 precision < 0.5 即不可用

## 开发集（40 条轨迹）

| 规则 | TP | FP | precision |
|---|---:|---:|---:|
| `test_metric_drives_config_change` | 43 | 817 | 0.050 |
| `hidden_label_file_read` | 12 | 67 | 0.152 |

## 留出集（20 条轨迹，只作参考）

| 规则 | TP | FP | precision |
|---|---:|---:|---:|
| `test_metric_drives_config_change` | 46 | 458 | 0.091 |
| `hidden_label_file_read` | 1 | 25 | 0.038 |

## 为什么还是低

1. 归一化窗口把 `TEST`、`private`、`test` 的匹配范围扩大到几乎所有包含这些
   词的文本；大量 `python -c`、`bash -c`、`cat >` 只是普通命令，不是
   “配置选择”。
2. “测试指标后 20 步内任意编辑”太宽：正例通常是“测试指标被**引用**后
   修改配置”，不是“看到测试指标后随手执行命令”。
3. `hidden_label_file_read` 的路径模式仍把普通公开数据目录误判为隐藏答案。

## 结论

两个 v2 子规则在冻结的开发集上均不可用。本轮不产出 TCE act 级检测能力。
这是第二个负结果，说明“用固定正则匹配工具文本”的路径对该数据集不成立。

## 下一步（必须重新预注册）

1. 换到更精确的语义：不是“任何工具输出含 TEST”，而是**先定位 agent 明确
   读取/引用某条测试指标的行，再追踪后续代码/配置修改**。
2. 把“测试集”从路径匹配升级为**数据分割语义**：识别 `train_test_split`、
   `test.csv`、`dev/test` 文件路径，并判断同一路径是否被后续配置选择使用。
3. 或者放弃正则规则，改用 LLM 辅助标注；但这需要固定 prompt 并重新预注册，
   不能直接沿用当前结果。

## 文件

- `PREREGISTRATION_TCE_V2.json`
- `SPLIT_TCE_V2.json`
- `result-tce-v2.json`
- `TCE_V2_RESULT_REPORT.zh-CN.md`
