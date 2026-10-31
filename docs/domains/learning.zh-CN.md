# 学习域（learning）量化指南

学科、技能、阅读与学习工具——投入与掌握度并行的能力积累维度。

> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。

## 指标总览

| 类别 | 指标数 | 方向 | 单位 |
|---|---|---|---|
| subjects | 60 | 越高越好 | hours、score |
| skills | 52 | 越高越好 | hours、score |
| study_tools | 24 | 越高越好 | days、minutes |
| reading | 36 | 越高越好 | minutes、pages |
| languages | 24 | 越高越好 | hours、words |
| exams_certificates | 34 | 越高越好 | hours、ratio |
| courses | 20 | 越高越好 | hours、items |
| **合计** | **250** | | |

## 类别详解

### subjects

维度模板：`hours`：范围 0–8hours，越高越好，建议 7 次/窗口；`mastery`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| mathematics | 越高越好 | hours | — |
| physics | 越高越好 | hours | — |
| chemistry | 越高越好 | hours | — |
| biology | 越高越好 | hours | — |
| english | 越高越好 | hours | — |
| chinese | 越高越好 | hours | — |
| history | 越高越好 | hours | — |
| geography | 越高越好 | hours | — |
| politics | 越高越好 | hours | — |
| programming | 越高越好 | hours | — |
| economics | 越高越好 | hours | — |
| psychology | 越高越好 | hours | — |
| philosophy | 越高越好 | hours | — |
| literature | 越高越好 | hours | — |
| law | 越高越好 | hours | — |
| medicine | 越高越好 | hours | — |
| engineering | 越高越好 | hours | — |
| design | 越高越好 | hours | — |
| music | 越高越好 | hours | — |
| art | 越高越好 | hours | — |
| physical_ed | 越高越好 | hours | — |
| statistics | 越高越好 | hours | — |
| logic | 越高越好 | hours | — |
| astronomy | 越高越好 | hours | — |
| geology | 越高越好 | hours | — |
| linguistics | 越高越好 | hours | — |
| sociology | 越高越好 | hours | — |
| anthropology | 越高越好 | hours | — |
| neuroscience | 越高越好 | hours | — |
| finance_study | 越高越好 | hours | — |

### skills

维度模板：`hours`：范围 0–8hours，越高越好，建议 7 次/窗口；`level`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| reading | 越高越好 | hours | — |
| writing | 越高越好 | hours | — |
| speaking | 越高越好 | hours | — |
| listening | 越高越好 | hours | — |
| translation | 越高越好 | hours | — |
| algorithm | 越高越好 | hours | — |
| system_design | 越高越好 | hours | — |
| data_analysis | 越高越好 | hours | — |
| communication | 越高越好 | hours | — |
| leadership | 越高越好 | hours | — |
| negotiation | 越高越好 | hours | — |
| programming_lang | 越高越好 | hours | — |
| framework | 越高越好 | hours | — |
| tooling | 越高越好 | hours | — |
| notetaking | 越高越好 | hours | — |
| shorthand | 越高越好 | hours | — |
| search | 越高越好 | hours | — |
| analysis | 越高越好 | hours | — |
| modeling | 越高越好 | hours | — |
| experiment | 越高越好 | hours | — |
| paper_writing | 越高越好 | hours | — |
| code_review | 越高越好 | hours | — |
| testing | 越高越好 | hours | — |
| deployment | 越高越好 | hours | — |
| public_speaking | 越高越好 | hours | — |
| teaching | 越高越好 | hours | — |

### study_tools

维度模板：`minutes`：范围 0–240minutes，越高越好，建议 7 次/窗口；`usage_days`：范围 0–7days，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| textbook | 越高越好 | minutes | — |
| notes | 越高越好 | minutes | — |
| problem_bank | 越高越好 | minutes | — |
| video_course | 越高越好 | minutes | — |
| podcast | 越高越好 | minutes | — |
| paper | 越高越好 | minutes | — |
| documentation | 越高越好 | minutes | — |
| code_repo | 越高越好 | minutes | — |
| online_course | 越高越好 | minutes | — |
| laboratory | 越高越好 | minutes | — |
| flashcards | 越高越好 | minutes | — |
| simulator | 越高越好 | minutes | — |

### reading

维度模板：`pages`：范围 0–500pages，越高越好，建议 7 次/窗口；`minutes`：范围 0–300minutes，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| fiction | 越高越好 | pages | — |
| nonfiction | 越高越好 | pages | — |
| academic | 越高越好 | pages | — |
| technical | 越高越好 | pages | — |
| biography | 越高越好 | pages | — |
| history_book | 越高越好 | pages | — |
| philosophy_book | 越高越好 | pages | — |
| poetry | 越高越好 | pages | — |
| essay | 越高越好 | pages | — |
| manga | 越高越好 | pages | — |
| news_article | 越高越好 | pages | — |
| blog | 越高越好 | pages | — |
| newsletter | 越高越好 | pages | — |
| magazine | 越高越好 | pages | — |
| manual | 越高越好 | pages | — |
| report | 越高越好 | pages | — |
| tutorial | 越高越好 | pages | — |
| diary | 越高越好 | pages | — |

### languages

维度模板：`hours`：范围 0–8hours，越高越好，建议 7 次/窗口；`words`：范围 0–500words，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| english_vocab | 越高越好 | hours | — |
| japanese_vocab | 越高越好 | hours | — |
| korean_vocab | 越高越好 | hours | — |
| french_vocab | 越高越好 | hours | — |
| german_vocab | 越高越好 | hours | — |
| spanish_vocab | 越高越好 | hours | — |
| chinese_learning | 越高越好 | hours | — |
| japanese_grammar | 越高越好 | hours | — |
| english_listening | 越高越好 | hours | — |
| english_speaking | 越高越好 | hours | — |
| english_reading | 越高越好 | hours | — |
| english_writing | 越高越好 | hours | — |

### exams_certificates

维度模板：`hours`：范围 0–8hours，越高越好，建议 30 次/窗口；`progress`：范围 0–1ratio，越高越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| cet4 | 越高越好 | hours | — |
| cet6 | 越高越好 | hours | — |
| ielts | 越高越好 | hours | — |
| toefl | 越高越好 | hours | — |
| gre | 越高越好 | hours | — |
| gmat | 越高越好 | hours | — |
| kaoyan | 越高越好 | hours | — |
| civil_service | 越高越好 | hours | — |
| teacher_cert | 越高越好 | hours | — |
| accounting_cert | 越高越好 | hours | — |
| programmer_cert | 越高越好 | hours | — |
| software_engineer | 越高越好 | hours | — |
| pmp | 越高越好 | hours | — |
| driver_license | 越高越好 | hours | — |
| python_cert | 越高越好 | hours | — |
| machine_learning_cert | 越高越好 | hours | — |
| data_science_cert | 越高越好 | hours | — |

### courses

维度模板：`hours`：范围 0–8hours，越高越好，建议 30 次/窗口；`completed`：范围 0–20items，越高越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| mooc | 越高越好 | hours | — |
| udemy | 越高越好 | hours | — |
| coursera | 越高越好 | hours | — |
| edx | 越高越好 | hours | — |
| youtube_lecture | 越高越好 | hours | — |
| bilibili_course | 越高越好 | hours | — |
| workshop | 越高越好 | hours | — |
| bootcamp | 越高越好 | hours | — |
| seminar | 越高越好 | hours | — |
| tutorial_series | 越高越好 | hours | — |
