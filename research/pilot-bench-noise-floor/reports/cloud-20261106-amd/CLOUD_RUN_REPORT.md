# AMD Radeon Cloud 复算报告（2026-11-06）

平台：`root@36.150.116.206 -p 36095`，128 vCPU / 503GB 内存 /
1.6TB 可用，1× AMD Radeon GPU。本次只使用 CPU，未使用 GPU。

依赖：Python 3.12.3，离线安装 numpy 2.2.6 + pandas 2.2.3
（cp312 wheel + pytz/dateutil/tzdata）。未使用 GPU 计算。

## 1. AJB 3,200 板重数

- 结果：3,200 boards，3,020 UNREADABLE，180 MARGINAL，0 READABLE。
- `status=passed`
- 回执 SHA-256：`e9730ebd86c98d00bc04db6cd4d88eda2577edfb7b2c8c07b7944608daf0d07b`

与 SCNet 结果一致（计数相同，回执哈希因平台字段不同而不同）。

## 2. A2 estimand split

- 20/20 钉住哈希匹配；F1-F5 全部 PASS。
- `status=completed`
- 回执 SHA-256：`a617fc2776baf3734d31b4b2094c891a771c5a16b5df90c12dc3cc200eb20896`

## 3. A3 v1.1 双跑

- 使用 v1.1 预注册（`ae6f12e4…`）与 worktree runner（`f688db9c…`）。
- 两次输出字节一致：`4fd64d0e3aa64f2f884de1295dc444574428f338da165c45c07062babd0a6ffb`
- 与 SCNet 上 v1.1 双跑结果**完全相同**，构成跨平台可复现证据。

## 4. 说明

- 三项都是 CPU 复算，未消耗 GPU。
- 未上传论文、未投稿、未提交、未推送。

## 5. 全量对抗评审（本机 Magpie）

在 AMD 复算完成后，用本机 Magpie 对 16 条主张跑了 1 轮全量对抗评审
（`kiro/deepseek-3.2`）：

- clean 7 / objected 9 / inconclusive 0。
- objected：C02-C09、C12。
- rebuttal 分类：7 executable、0 out_of_loop、4 unclassified。
- 最终决策：`rollback`（机械检查失败 + 9 条异议 + 11 项诚信检查未评估）。

回执：`reports/ai-review-20261105/adversarial-full/summary.json`，
SHA-256 `c978b77bd4f387b9a1bc61968ccc9f2ed4da0a07aed618e96813a746b85e271b`。
