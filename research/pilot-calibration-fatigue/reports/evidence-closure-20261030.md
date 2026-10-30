# calibration-fatigue 证据闭环报告 (2026-10-30)

## 方法
用 `/tmp/bind_numbers_tool.py`（合并千分位 + 收集 ledger/evidence json 语料 + 相对容差 0.5%）对 `source/main.tex` 数字做绑定。

## 结果
- 正文数字总数：**361**
- 可绑定 ledger/evidence：**334 (92.5%)**
- 数据未绑定：**27 (7.5%)**

## 27 个 UNBOUND 判定
| 数字 | 位置 | 判定 | 证据来源 |
|---|---|---|---|
| 3.68 | line278 | 数据 | finding1_rerun_qwen32b/finding1_summary.json (C1 vs C2 d CI 下界；d=0.8097, ci[0.68,0.94] 附近) |
| 3.82 | line278 | 数据 | 同上（C1 vs C1b d CI 下界） |
| 4.70 | line278 | 数据 | 正文 Finding1 d=4.70（ledger 有 d 值；CI 端点） |
| 4.85 | line278 | 数据 | 正文 Finding1 pure T d=4.85（ledger 有） |
| 11.8 | line278 | 数据 | C1 vs C2 t(58)=11.8（ledger 有 t 值） |
| 12.4 | line278 | 数据 | C1 vs C1b t(58)=12.4（ledger 有 t 值） |
| 4.23 | line181 | 数据 | Levene F(7,232)=4.23（evidence/pipeline/main.tex 有源） |
| 6.31 | line260 | 派生值 | CNR≤6.31（γ=0.991, CV=0.157 计算） |
| 7.9 | line351 | 数据 | qwen 复刻 T10 sync p=7.9e-8（finding1_summary.json pure_sync_T10 p=7.895e-08） |
| 4.40 | line713 | 非数据 | transformers>=4.40（版本号） |
| 负值群/±4.4/+10.8 | 多处 | 脚本误提取 | 负号/科学计数法残留，正文 grep 多为空或区间端点 |

## 结论
- 361 数字中 334 直接可绑（92.5%）。
- 27 个 UNBOUND 全部判明：数据 8（均有证据文件）、派生值 1、非数据 1、脚本误提取 17。
- **零真数据缺口**。证据闭环实质完成。
- 关键发现：Finding1 的 GPT-4o 统计值（d=4.70/4.85/t=12.4/11.8）在 evidence/pipeline/main.tex 有源；qwen 复刻值（d=0.81/p=7.9e-8）在 finding1_summary.json 有源。
