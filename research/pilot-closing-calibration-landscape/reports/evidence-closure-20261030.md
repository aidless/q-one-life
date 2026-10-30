# closing-calibration-landscape 证据闭环报告 (2026-10-30)

## 方法
用 `/tmp/bind_numbers_tool.py`（合并千分位 + 收集 ledger/evidence json 语料 + 相对容差 0.5%）对 `source/main.tex` 数字做绑定。

## 结果
- 正文数字总数：**56**
- 可绑定 ledger/evidence：**44 (78.6%)**
- 非数据：**5 (8.9%)**
- 数据未绑定：**7 (12.5%)**

## 7 个 UNBOUND 判定
| 数字 | 位置 | 判定 |
|---|---|---|
| -122/-74/-37 | (正文 grep 空) | 脚本误提取 |
| 2.42 | line55 | 引用转述（liu2026caleffects 先验：DeepSeek self-eval CV=2.42） |
| 8.5 | line45/57 | 引用转述（liu2026caleffects 先验：CV↑8.5%） |
| 37 | line45/57 | 引用转述（liu2026caleffects 先验：35--37%） |
| 99 | line155 | 非数据（thebibliography{99}） |

## 结论
- 56 数字中 44 直接可绑，7 个全部判明（引用转述 3 + 非数据 1 + 脚本误提取 3）。
- **零真数据缺口**。证据闭环实质完成。
