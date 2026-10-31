# 恢复域（recovery）量化指南

恢复技巧、恢复指标与休息日——主动恢复的可度量维度。

> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。

## 指标总览

| 类别 | 指标数 | 方向 | 单位 |
|---|---|---|---|
| techniques | 40 | 越高越好 | minutes、score |
| metrics | 20 | 越高越好 | index、score |
| rest_days | 7 | 越高越好 | days |
| sleep_hygiene | 10 | 越高越好 | score |
| body_recovery | 16 | 越高越好 | days、score |
| **合计** | **93** | | |

## 类别详解

### techniques

维度模板：`minutes`：范围 0–180minutes，越高越好，建议 7 次/窗口；`quality`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| meditation | 越高越好 | minutes | — |
| breathing | 越高越好 | minutes | — |
| mindfulness | 越高越好 | minutes | — |
| walk | 越高越好 | minutes | — |
| massage | 越高越好 | minutes | — |
| hot_bath | 越高越好 | minutes | — |
| music | 越高越好 | minutes | — |
| reading | 越高越好 | minutes | — |
| nap | 越高越好 | minutes | — |
| yoga | 越高越好 | minutes | — |
| stretching | 越高越好 | minutes | — |
| journaling | 越高越好 | minutes | — |
| venting | 越高越好 | minutes | — |
| gardening | 越高越好 | minutes | — |
| petting | 越高越好 | minutes | — |
| cooking | 越高越好 | minutes | — |
| tea | 越高越好 | minutes | — |
| aromatherapy | 越高越好 | minutes | — |
| sauna | 越高越好 | minutes | — |
| acupuncture | 越高越好 | minutes | — |

### metrics

维度模板：`value`：范围 0–100index，越高越好，建议 7 次/窗口；`score`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| heart_rate_variability | 越高越好 | index | — |
| resting_heart_rate | 越高越好 | index | — |
| muscle_soreness | 越高越好 | index | — |
| fatigue | 越高越好 | index | — |
| attention | 越高越好 | index | — |
| memory | 越高越好 | index | — |
| reaction_time | 越高越好 | index | — |
| stress_index | 越高越好 | index | — |
| recovery_quality | 越高越好 | index | — |
| sleep_debt | 越高越好 | index | — |

### rest_days

维度模板：`days`：范围 0–7days，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| full_rest | 越高越好 | days | — |
| active_rest | 越高越好 | days | — |
| digital_detox | 越高越好 | days | — |
| nature_day | 越高越好 | days | — |
| social_rest | 越高越好 | days | — |
| creative_rest | 越高越好 | days | — |
| silent_rest | 越高越好 | days | — |

### sleep_hygiene

维度模板：`quality`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| consistent_schedule | 越高越好 | score | — |
| cool_room | 越高越好 | score | — |
| dark_room | 越高越好 | score | — |
| quiet_room | 越高越好 | score | — |
| no_caffeine_evening | 越高越好 | score | — |
| no_screen_bed | 越高越好 | score | — |
| comfortable_bed | 越高越好 | score | — |
| pre_sleep_routine | 越高越好 | score | — |
| no_late_meals | 越高越好 | score | — |
| morning_light | 越高越好 | score | — |

### body_recovery

维度模板：`score`：范围 0–10score，越高越好，建议 7 次/窗口；`days`：范围 0–7days，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| muscle_recovery | 越高越好 | score | — |
| joint_mobility | 越高越好 | score | — |
| flexibility | 越高越好 | score | — |
| posture | 越高越好 | score | — |
| breath_quality | 越高越好 | score | — |
| digestion | 越高越好 | score | — |
| immune_status | 越高越好 | score | — |
| inflammation | 越高越好 | score | — |
