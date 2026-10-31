# 工作域（work）量化指南

任务、项目、会议与工具——把工作投入与产出都纳入量化。

> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。

## 指标总览

| 类别 | 指标数 | 方向 | 单位 |
|---|---|---|---|
| tasks | 36 | 越高越好 | hours、ratio |
| projects | 36 | 越高越好 | hours、ratio |
| meetings | 12 | 越低越好 | minutes |
| tools | 44 | 越高越好 | hours、score |
| deliverables | 14 | 越高越好 | items |
| performance | 16 | 越高越好 | hours、score |
| career | 16 | 越高越好 | hours、ratio |
| communication | 16 | 越高越好 | items、score |
| **合计** | **190** | | |

## 类别详解

### tasks

维度模板：`hours`：范围 0–8hours，越高越好，建议 7 次/窗口；`completion`：范围 0–1ratio，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| coding | 越高越好 | hours | — |
| code_review | 越高越好 | hours | — |
| meeting | 越高越好 | hours | — |
| documentation | 越高越好 | hours | — |
| testing | 越高越好 | hours | — |
| deployment | 越高越好 | hours | — |
| research | 越高越好 | hours | — |
| design | 越高越好 | hours | — |
| debugging | 越高越好 | hours | — |
| performance_opt | 越高越好 | hours | — |
| refactoring | 越高越好 | hours | — |
| requirement_analysis | 越高越好 | hours | — |
| design_review | 越高越好 | hours | — |
| reporting | 越高越好 | hours | — |
| recruiting | 越高越好 | hours | — |
| training | 越高越好 | hours | — |
| incident_response | 越高越好 | hours | — |
| planning | 越高越好 | hours | — |

### projects

维度模板：`hours`：范围 0–8hours，越高越好，建议 7 次/窗口；`progress`：范围 0–1ratio，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| frontend | 越高越好 | hours | — |
| backend | 越高越好 | hours | — |
| data | 越高越好 | hours | — |
| algorithm | 越高越好 | hours | — |
| infrastructure | 越高越好 | hours | — |
| security | 越高越好 | hours | — |
| testing_eng | 越高越好 | hours | — |
| operations | 越高越好 | hours | — |
| mobile | 越高越好 | hours | — |
| desktop | 越高越好 | hours | — |
| api | 越高越好 | hours | — |
| database | 越高越好 | hours | — |
| docs_site | 越高越好 | hours | — |
| monitoring | 越高越好 | hours | — |
| ci | 越高越好 | hours | — |
| release | 越高越好 | hours | — |
| machine_learning | 越高越好 | hours | — |
| llm | 越高越好 | hours | — |

### meetings

维度模板：`duration`：范围 0–240minutes，越低越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| standup | 越低越好 | minutes | — |
| weekly | 越低越好 | minutes | — |
| monthly | 越低越好 | minutes | — |
| quarterly | 越低越好 | minutes | — |
| review | 越低越好 | minutes | — |
| retrospective | 越低越好 | minutes | — |
| one_on_one | 越低越好 | minutes | — |
| client | 越低越好 | minutes | — |
| vendor | 越低越好 | minutes | — |
| interview | 越低越好 | minutes | — |
| sync | 越低越好 | minutes | — |
| all_hands | 越低越好 | minutes | — |

### tools

维度模板：`hours`：范围 0–8hours，越高越好，建议 7 次/窗口；`proficiency`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| git | 越高越好 | hours | — |
| vim | 越高越好 | hours | — |
| docker | 越高越好 | hours | — |
| kubernetes | 越高越好 | hours | — |
| jupyter | 越高越好 | hours | — |
| sql | 越高越好 | hours | — |
| spark | 越高越好 | hours | — |
| linux | 越高越好 | hours | — |
| ci_cd | 越高越好 | hours | — |
| terraform | 越高越好 | hours | — |
| ansible | 越高越好 | hours | — |
| grafana | 越高越好 | hours | — |
| prometheus | 越高越好 | hours | — |
| kafka | 越高越好 | hours | — |
| redis | 越高越好 | hours | — |
| postgresql | 越高越好 | hours | — |
| mongodb | 越高越好 | hours | — |
| elasticsearch | 越高越好 | hours | — |
| airflow | 越高越好 | hours | — |
| dbt | 越高越好 | hours | — |
| snowflake | 越高越好 | hours | — |
| databricks | 越高越好 | hours | — |

### deliverables

维度模板：`count`：范围 0–50items，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| feature | 越高越好 | items | — |
| bugfix | 越高越好 | items | — |
| pull_request | 越高越好 | items | — |
| release | 越高越好 | items | — |
| migration | 越高越好 | items | — |
| schema_change | 越高越好 | items | — |
| incident | 越高越好 | items | — |
| hotfix | 越高越好 | items | — |
| docs_page | 越高越好 | items | — |
| test_case | 越高越好 | items | — |
| commit | 越高越好 | items | — |
| code_snippet | 越高越好 | items | — |
| architecture_doc | 越高越好 | items | — |
| runbook | 越高越好 | items | — |

### performance

维度模板：`score`：范围 0–10score，越高越好，建议 7 次/窗口；`hours`：范围 0–8hours，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| focused_hours | 越高越好 | score | — |
| flow_state | 越高越好 | score | — |
| productivity | 越高越好 | score | — |
| output_quality | 越高越好 | score | — |
| task_completion | 越高越好 | score | — |
| deep_work | 越高越好 | score | — |
| shallow_work | 越高越好 | score | — |
| interruption_count | 越高越好 | score | — |

### career

维度模板：`progress`：范围 0–1ratio，越高越好，建议 30 次/窗口；`hours`：范围 0–8hours，越高越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| promotion | 越高越好 | ratio | — |
| salary_negotiation | 越高越好 | ratio | — |
| skill_development | 越高越好 | ratio | — |
| job_switch | 越高越好 | ratio | — |
| portfolio | 越高越好 | ratio | — |
| interview_prep | 越高越好 | ratio | — |
| resume_update | 越高越好 | ratio | — |
| network_events | 越高越好 | ratio | — |

### communication

维度模板：`count`：范围 0–50items，越高越好，建议 7 次/窗口；`quality`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| email_sent | 越高越好 | items | — |
| slack_message | 越高越好 | items | — |
| doc_reviewed | 越高越好 | items | — |
| presentation | 越高越好 | items | — |
| code_comment | 越高越好 | items | — |
| design_doc | 越高越好 | items | — |
| standup_update | 越高越好 | items | — |
| feedback_given | 越高越好 | items | — |
