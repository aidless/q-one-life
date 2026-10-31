# 精力域（energy）量化指南

睡眠阶段、消耗与增益——精力从哪里来、又流向哪里。

> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。

## 指标总览

| 类别 | 指标数 | 方向 | 单位 |
|---|---|---|---|
| sleep_stages | 24 | 越高越好 | minutes、score |
| drainers | 12 | 越低越好 | score |
| boosters | 12 | 越高越好 | minutes |
| circadian | 12 | 越高越好 | minutes、score |
| **合计** | **60** | | |

## 类别详解

### sleep_stages

维度模板：`minutes`：范围 0–480minutes，越高越好，建议 7 次/窗口；`score`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| deep_sleep | 越高越好 | minutes | — |
| light_sleep | 越高越好 | minutes | — |
| rem | 越高越好 | minutes | — |
| awake | 越高越好 | minutes | — |
| sleep_latency | 越高越好 | minutes | — |
| sleep_efficiency | 越高越好 | minutes | — |
| sleep_duration | 越高越好 | minutes | — |
| time_in_bed | 越高越好 | minutes | — |
| sleep_regularity | 越高越好 | minutes | — |
| nap | 越高越好 | minutes | — |
| bedtime | 越高越好 | minutes | — |
| wake_time | 越高越好 | minutes | — |

### drainers

维度模板：`amount`：范围 0–10score，越低越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| caffeine | 越低越好 | score | — |
| alcohol | 越低越好 | score | — |
| nicotine | 越低越好 | score | — |
| sugar | 越低越好 | score | — |
| sedentary | 越低越好 | score | — |
| screen | 越低越好 | score | — |
| late_night | 越低越好 | score | — |
| bright_light | 越低越好 | score | — |
| noise | 越低越好 | score | — |
| dehydration | 越低越好 | score | — |
| overwork | 越低越好 | score | — |
| caffeine_afternoon | 越低越好 | score | — |

### boosters

维度模板：`minutes`：范围 0–120minutes，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| morning_light | 越高越好 | minutes | — |
| exercise | 越高越好 | minutes | — |
| hydration | 越高越好 | minutes | — |
| nutrition | 越高越好 | minutes | — |
| socializing | 越高越好 | minutes | — |
| music | 越高越好 | minutes | — |
| nature | 越高越好 | minutes | — |
| power_nap | 越高越好 | minutes | — |
| breathing | 越高越好 | minutes | — |
| stretching | 越高越好 | minutes | — |
| cold_shower | 越高越好 | minutes | — |
| sunlight | 越高越好 | minutes | — |

### circadian

维度模板：`score`：范围 0–10score，越高越好，建议 7 次/窗口；`minutes`：范围 0–120minutes，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| morning_alertness | 越高越好 | score | — |
| evening_fatigue | 越高越好 | score | — |
| meal_timing | 越高越好 | score | — |
| caffeine_cutoff | 越高越好 | score | — |
| light_exposure | 越高越好 | score | — |
| chronotype_score | 越高越好 | score | — |
