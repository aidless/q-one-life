# Q-One Life 评审材料包 — 事实摘录（非评价）

> 本文件仅包含可核验事实，供评委独立打分。所有数字均可从仓库复现。

## 1. 项目概况

| 项 | 事实 |
|---|---|
| 名称 | Q-One Life |
| 版本 | 0.8.0.dev0 |
| 定位 | 本地优先、证据可审计的个人决策 Agent + Research Factory |
| 许可证 | MIT（LICENSE 1075 字节） |
| 仓库 | github.com/aidless/q-one-life |
| 分支 | main @ 3922e43，ahead origin/main 27 提交 |
| 提交总数 | 40（全部近 30 天） |
| 远端 | origin https://github.com/aidless/q-one-life.git |

## 2. 代码规模

| 项 | 事实 |
|---|---|
| src/qone_life 模块数 | 26 个 .py |
| 代码总行数 | 8,203（src）+ 测试合计 11,938 |
| 最大模块 | research_factory.py 1811 行 |
| 模块行数分布 | research.py 1246 / web.py 892 / cli.py 606 / encrypted_backup.py 345 / research_production.py 315 / planner.py 313 |
| 测试文件 | 23 个 |
| schema | 5 个（arxiv-package-audit / observation / paper-portfolio / research-project / research-triage） |

## 3. 测试与质量

| 项 | 事实 |
|---|---|
| pytest | 196 passed + 22 subtests（15.53s，1 warning） |
| ruff check | 37 errors（E402×10, W1510×3, F401×3, E001×3, F100×2, F102×1, RUF100×若干）；22 fixable |
| schema JSON 有效性 | 5/5 有效 |
| pyproject | ruff line-length 100, target py310；MIT；requires-python >=3.10 |
| 依赖 | fastapi 0.115.6, uvicorn 0.34.0, q-one-core git@b1f41de, q-one-agent git@79a951a |

## 4. 生活层量化系统

| 项 | 事实 |
|---|---|
| 指标目录 | examples/metric-spec.json — **1644 指标**，10 域，18,159 行 |
| 域分布 | learning 250 / finance 243 / health 212 / work 190 / other 153 / environment 152 / social 136 / emotion 127 / recovery 93 / energy 88 |
| 方向 | higher 1289 / lower 282 / target 73 |
| 域文档 | docs/domains/*.zh-CN.md 10 份，19,827 行（CATALOG 同源生成，test_domain_docs_sync 5/5） |
| 功能闭环 | 观察(add-observation)→打分(score 方向感知归一化)→迭代(iterate 日聚合/环比/趋势)→建议(suggest 按 direction)→web(/api/scores /api/iterate /api/suggest) |
| 核心模块 | models.py(MetricSpec/Observation), scoring.py(_normalized_by_direction/_aggregate_scores), iteration.py(daily_iteration), suggestion.py(suggest_improvements) |

## 5. 科研工厂

| 项 | 事实 |
|---|---|
| 90 天计划 | D1-D15 ✅ / D16-D30 ⏸ / D31-D45 ✅机械 / D46-D60 ✅ / D61-D75 ⚠️部分 / D76-D90 ⏸ |
| pilot | 17 个（5 试点 revision / 6 review_pending / 4 blocked / 4 archived），全部 valid=True ready=False |
| PAPER_PLAN | 5/5 |
| 独立评审 | 5/5 |
| citation-verification | 3/3 |
| 机械打包 | 3/5（paper11/bench/f-acceptance 有 tar.gz + clean-room exit 0） |
| 未闭合 | bench C02/C03、f-acceptance C11、arc C09、gemma 源身份、gemma/arc LaTeX 工具链、5 篇 arXiv 上传（用户门）、133 族人工处置 |
| 量化 | RESEARCH_QUANTIFICATION.zh-CN.md 8 对象 + 7 规则 + 7 可计算量（quantify_research_project 首次实现） |

## 6. 关键事实

| 项 | 事实 |
|---|---|
| 发布状态 | Linux x64 unsigned-internal；未签名、未公证、未公开发布 |
| 数据保护 | SQLite 受 OS ACL 保护；加密范围是 .qonebackup 备份容器，非端到端加密 |
| 入口 | qone-life CLI（main() @ cli.py:565）；桌面 Electron/TS 外壳 + PyInstaller sidecar |
| 无模型降级 | 无模型时规则推荐仍能完成目标/行动/反馈/备份/恢复 |

## 7. 文档清单

docs/：ACCEPTANCE / AUTOMATIC_RECOMMENDATIONS / BLUEPRINT / DECISION_STUDIO / LIFE_SYSTEM / ONTOLOGY / OUTCOME_INTAKE / PRIVACY / RESEARCH_FACTORY_90_DAY_PLAN / RESEARCH_FACTORY_AUTONOMOUS_ITERATION_PLAN / RESEARCH_QUANTIFICATION / SCORING / SYNTHESIS_IMPLEMENTATION / USER_GUIDE + domains/×10 + research/ + blog/ + demo/ + career/ + evidence/
