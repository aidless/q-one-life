# F9 (2×2 Comm×Cal) 分析报告与均匀实验方案

> **日期**：2026-09-01
> **数据来源**：`archived_joint_2x2_30seed_20260811.json`（FLAGSHIP manuscript #48 archived predecessor）
> **关键发现**：① archived 文件数据聚合有 bug（A/C/D 的 gamma 数据逐位重复）；② B 条件 T 值不均一影响高度显著（B1 vs B2, t=5.69, p<0.0001）；③ 此文件不可用于正式分析，需用 Phase 54 数据或重新运行。

---

## 一、数据质量审计

### 1.1 严重问题：A/C/D 数据重复

逐位比对发现，A（no comm, no cal）、C（no comm, cal）、D（comm, cal）三个条件的 `final_gamma_mean_per_rep`（30 个值）**完全相同**：

```
A: 0.7914, 0.7494, 0.6493, 0.6068, ..., 0.7382 (30 values)
C: 0.7914, 0.7494, 0.6493, 0.6068, ..., 0.7382 (identical)
D: 0.7914, 0.7494, 0.6493, 0.6068, ..., 0.7382 (identical)
```

只有 B（comm, no cal）条件的数据不同。

**原因推测**：聚合脚本 `archived_joint_2x2_30seed_20260811.json` 在汇总 120 个原始文件时，可能错误地把 A 条件的 per-seed 数据复制到了 C 和 D。

**结论**：此文件的 A/C/D 对比不可信，不能用于正式分析。

### 1.2 文件元数据的自我标注

文件明确标注：
> "This 2x2 x 30 archive is NOT the basis of the manuscript's main claims; it is included as transparent per-seed record-keeping evidence."
>
> "The manuscript's cited joint experiment is Phase 54 (evidence/joint_full_F_v10_results.json, 125 sessions, deepseek-v4-flash, 5 tasks x 5 seeds x 3 alpha x 2 T)."

**正式数据来源应为 Phase 54**（`joint_full_F_v10_results.json`，125 sessions），而非此 archived 文件。

---

## 二、B 条件 T 值不均一分析（可信部分）

虽然 A/C/D 数据有问题，但 B 条件内部的 B1/B2 对比不受影响（同一条件内的 30 个 seed 是独立运行的）。

### 2.1 设计说明

- B 条件（comm, no cal）的 30 个 seeds：
  - seeds 0-14（B1）：T=20 轮
  - seeds 15-29（B2）：T=30 轮
- 不均一原因：实验运行过程中 T 值从 20 调整为 30，前 15 个 seed 用旧参数

### 2.2 分层统计（gamma 指标）

| 组 | n | T | mean gamma | sd | se |
|----|---|---|------------|-----|-----|
| B1 | 15 | 20 | **0.8586** | 0.0969 | 0.0250 |
| B2 | 15 | 30 | **0.6864** | 0.0660 | 0.0170 |

**独立样本 t 检验（Welch）**：
- t = 5.69
- df = 24.7
- **p < 0.0001**（高度显著）
- Cohen's d = 2.08（极大效应量）

**结论**：T 值从 20 增加到 30，gamma 均值从 0.859 降到 0.686（下降 20%），影响高度显著。B 条件绝对不能合并 B1+B2，必须分层分析或重新运行。

### 2.3 对原分析的影响

原汇总中 B=0.3720（ECE 指标）是合并 B1+B2 的结果，这个合并在统计上是不合理的（两组来自不同分布）。正确的做法：
- 要么分别报告 B1(T=20) 和 B2(T=30)
- 要么重新运行统一 T=30 的 B 条件（与 A/C/D 一致）

---

## 三、均匀实验方案（三选一）

### 方案 A：使用 Phase 54 正式数据（推荐，无需重新运行）

**数据来源**：`F:\Research\PAPER13_MERGED\evidence\joint_full_F_v10_results.json`
- 125 sessions
- deepseek-v4-flash
- 5 tasks × 5 seeds × 3 alpha × 2 T
- 这是主稿引用的正式实验

**操作**：
1. 从 Phase 54 数据中提取 2×2 Comm×Cal 子集
2. 确保 T 值统一（或分层分析 T=20/T=30）
3. 重新计算 A/B/C/D 的均值、标准差、2×2 ANOVA
4. 验证 Comm 主效应、Cal 主效应、Comm×Cal 交互

**优点**：数据质量有保障，是主稿已引用的正式数据
**缺点**：需要确认 Phase 54 是否有完整的 2×2 结构

### 方案 B：重新运行统一 T 的 2×2 实验（最干净）

**操作**：
1. 统一 T=30（与 A/C/D 一致）
2. 重新运行 B 条件的 30 个 seeds
3. 或者全部 4 个条件各重新运行 30 seeds，统一所有参数
4. 使用 `joint_experiment.py`（如果存在）或写新的运行脚本

**优点**：数据完全均匀，统计分析最干净
**缺点**：需要运行时间（30 seeds × 4 条件，可能需要几小时到几天）

### 方案 C：分层分析现有数据（最快，但有局限）

**操作**：
1. 把 B 拆成 B1(T=20, n=15) 和 B2(T=30, n=15)
2. 分别做两个 2×2 分析：
   - T=20 组：A(30), B1(15), C(30), D(30)
   - T=30 组：A(30), B2(15), C(30), D(30)
3. 用混合效应模型，把 T 值作为协变量
4. 在论文中透明报告 B 条件的 T 值设计和分层分析结果

**优点**：不需要重新运行，最快
**缺点**：
- A/C/D 数据有重复 bug（见第一节），分析结果不可信
- B1/B2 样本量减半（n=15），统计功效降低
- 只能作为探索性分析，不能作为正式结论

---

## 四、推荐方案与执行步骤

**推荐方案 A（使用 Phase 54 正式数据）**，理由：
1. archived 文件数据有 bug，不可用
2. Phase 54 是主稿已引用的正式数据，质量有保障
3. 不需要重新运行实验

**执行步骤**：
1. 检查 `F:\Research\PAPER13_MERGED\evidence\joint_full_F_v10_results.json` 是否存在及数据结构
2. 提取 2×2 Comm×Cal 子集（如果有）
3. 写分析脚本 `f9_phase54_analysis.py`，计算：
   - A/B/C/D 各条件的均值、标准差、95% CI
   - Comm 主效应、Cal 主效应、Comm×Cal 交互
   - 效应量（Cohen's d / η²）
   - 如果有 T 值分层，做 T 作为协变量的混合效应模型
4. 输出 `f9_phase54_results.md`

**如果 Phase 54 没有 2×2 结构**，则采用方案 B（重新运行），写统一 T=30 的运行脚本。

---

## 五、已完成的工作

1. ✅ 数据质量审计：发现 A/C/D 数据重复 bug
2. ✅ B 条件分层分析：B1 vs B2 t=5.69, p<0.0001
3. ✅ 分层分析脚本：`f9_stratified_analysis.py`（可运行，但因数据 bug 结果仅供参考）
4. ✅ 三方案对比与推荐

## 六、待完成

1. ⏳ 检查 Phase 54 数据是否存在及结构
2. ⏳ 如存在，写 `f9_phase54_analysis.py` 并运行
3. ⏳ 如不存在，写统一 T=30 的重新运行脚本
4. ⏳ 输出正式 F9 结果，更新因子报告
