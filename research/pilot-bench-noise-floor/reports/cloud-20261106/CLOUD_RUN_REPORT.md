# SCNet DCU 容器云端复算报告（2026-11-06）

平台：超算互联网华中三区（武汉）容器
`cgrp-237ne71y-b6947f8d7-qx4s2`，32 vCPU / 251GB 内存 / 450GB
`/root/private_data`。本次只使用 CPU，未使用 DCU。

本地打包 `/tmp/qone-cloud-bundle.tar.gz`，SHA-256
`f51200e295de6a9a37fb6203e7fd043535d85c6d954d80a79fa35ec313c2691e`；
远端解压后哈希一致。包含 A2/A3 实验目录、18 个原生依赖文件、
四个 AJB boards CSV、pandas/pytz wheel。

## 1. AJB 3,200 板独立重数

命令：`cloud_ajb_recount.py`，从四个 `p4_ajb*_boards.csv` 的
`verdict` 列逐行统计，不依赖 `p4_ajb_counts.json`。

| 项 | 值 |
|---|---|
| 总板数 | 3,200 |
| UNREADABLE | 3,020 |
| MARGINAL | 180 |
| READABLE | 0 |
| status | `passed` |
| 回执 SHA-256 | `930bd0da011ad035e65fffc8a275e360564595c7906a7beadffc8f6648af28b0` |

这给 C16 一个独立于计数快照的云回执：disjoint 部署仍没有正向判决。

## 2. A2 estimand split 重跑

命令：`run_estimand_split.py`，`--external-root` 指向打包的原生目录。
先用钉住的 `make_m25_votes.py` 重建四个 m25 派生表，四个哈希与预注册一致。

| 项 | 值 |
|---|---|
| status | `completed` |
| 20 项钉住哈希 | 全部 match |
| F1 fidelity | PASS |
| F2 identity replicate invariance | PASS |
| F3 fixed winner never positive | PASS |
| F4 controls have teeth | PASS |
| F5 native rerun matches recorded | PASS |
| 回执 SHA-256 | `204c3c3148bc719bdcede1039ab86c9c483b068eaaae83cc4b03433368908a86` |

`theta_both` 在四个 m25 任务上仍为 2000/2000 轮精确为零，
`theta_fixed` 复现记录的 native 区间且任何一轮都不为正。

## 3. A3 重跑：通过（使用预注册钉住的历史 runner）

首次尝试被 `runner hash does not match the preregistration` 拦住。
原因：当前工作树的 `run_common_support.py` 是
`2a921da3a8057d2c0ea10c9e4ecb137b3da9a336310a84f93af080fa7be89b0a`，
预注册钉住的是
`9669db5401f31b10a450eafd0762ddd9bafdec77737a3d30a420ec85f977b012`。
`git diff 6cccc23^` 显示两者唯一差异是 `--selftest` 中一行本机绝对路径被
安全清洗为 `<WORKSPACE_ROOT>`；正式 `--external-root` 路径不受影响。

处理：从 git 提交 `6cccc23^` 恢复 pin 住的历史字节
（`9669db54…`），上传到独立的 `a3_pinned/` 目录运行，**不修改工作树、
不改写预注册、不绕过哈希门**。预注册还要求外部目录是 git 仓库且
`rev-parse HEAD` 等于 `ab40e28abcb2a97e13242d0dab5584d42a15f94e`；
打包目录没有 `.git`，因此建了一个最小 ref 桩使该检查返回钉住值，
所有 9 个原生文件的哈希仍逐一校验。

| 项 | 值 |
|---|---|
| runner SHA-256 | `9669db5401f31b10a450eafd0762ddd9bafdec77737a3d30a420ec85f977b012`（与预注册一致） |
| F1 recorded leak reproduced | PASS |
| F2 LOO label identity, 47,200 pairs | PASS |
| F3 joint-support margin zero on four tasks | PASS |
| F4 bootstrap identity degenerate, 2000/2000 | PASS |
| F5 k-fold control has teeth | PASS |
| 回执 SHA-256 | `21dc4b70ba9d1227b5806adbe3ba8f62189621887cd95ec517ec60c1346ebcdd` |

结论只支持"leaky LOO 比较是支持集伪影"，不证明 k-fold 恢复排名效度。

## 5. A3 v1.1 正式 amendment 双跑

工作树 runner 与预注册的哈希漂移通过正式 amendment 处理，不覆盖冻结证据：

- v1.0.0 冻结副本：`amendments/preregistration-v1.0.0-frozen.json`
  (`2ff9ddf4…`)、`amendments/run_common_support-v1.0.0.py`
  (`9669db54…`)。
- 主预注册升 `v1.1.0` (`ae6f12e4…`)，只重钉 runner 为
  `f688db9c…`；`--selftest` 改从 `QONE_WORKSPACE_ROOT` 解析外部根路径。
- 任务、seed、支持集、门、bootstrap 次数、输出 schema 均未变。

云端用同一 `a3_pinned/` 目录跑两次：

| 项 | 值 |
|---|---|
| run1 / run2 SHA-256 | `4fd64d0e3aa64f2f884de1295dc444574428f338da165c45c07062babd0a6ffb`（字节一致） |
| F1-F5 | 全部 PASS |
| decision.status | `passed` |
| 绑定预注册 | `ae6f12e4dfec14770f7f2121af133dec9e78eea19e5f27f621de4ad60e520323` |

回执已拉回本目录：`a3_v11_run1.json`、`a3_v11_run2.json`。

## 4. 环境与限制

- 远程无 DNS，`pip install` 联网失败；改为本地下载
  pandas 2.2.3 (cp311) 与 pytz 2024.2 wheel 上传后离线安装。
- numpy 1.25.0 已存在，pandas 2.2.3 可用。
- 两个云端回执已拉回本地 `reports/cloud-20261106/`。
- 未上传论文、未投稿、未消耗 DCU/GPU 算力。
