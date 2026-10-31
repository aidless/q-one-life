# 其他域（other）量化指南

数字生活、习惯、目标、休闲与消费——不属于上述各域的杂项量化。

> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。

## 指标总览

| 类别 | 指标数 | 方向 | 单位 |
|---|---|---|---|
| digital_life | 24 | 越低越好 | hours、score |
| habits | 17 | 越高越好 | days |
| goals | 24 | 越高越好 | days、ratio |
| leisure | 18 | 越高越好 | minutes |
| consumption | 24 | 越低越好 | CNY、days |
| life_skills | 24 | 越高越好 | hours、score |
| personal_growth | 16 | 越高越好 | days、score |
| random_misc | 6 | 越高越好 | items、score |
| **合计** | **153** | | |

## 类别详解

### digital_life

维度模板：`hours`：范围 0–16hours，越低越好，建议 7 次/窗口；`score`：范围 0–10score，越低越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| screen_time | 越低越好 | hours | — |
| phone_usage | 越低越好 | hours | — |
| social_media | 越低越好 | hours | — |
| video | 越低越好 | hours | — |
| gaming | 越低越好 | hours | — |
| shopping | 越低越好 | hours | — |
| news | 越低越好 | hours | — |
| email | 越低越好 | hours | — |
| notifications | 越低越好 | hours | — |
| short_video | 越低越好 | hours | — |
| browsing | 越低越好 | hours | — |
| streaming | 越低越好 | hours | — |

### habits

维度模板：`days`：范围 0–7days，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| early_rise | 越高越好 | days | — |
| exercise | 越高越好 | days | — |
| reading | 越高越好 | days | — |
| hydration | 越高越好 | days | — |
| budgeting | 越高越好 | days | — |
| planning | 越高越好 | days | — |
| review | 越高越好 | days | — |
| decluttering | 越高越好 | days | — |
| saving | 越高越好 | days | — |
| studying | 越高越好 | days | — |
| meditation | 越高越好 | days | — |
| writing | 越高越好 | days | — |
| gratitude | 越高越好 | days | — |
| tidying | 越高越好 | days | — |
| walking | 越高越好 | days | — |
| flossing | 越高越好 | days | — |
| stretching | 越高越好 | days | — |

### goals

维度模板：`progress`：范围 0–1ratio，越高越好，建议 30 次/窗口；`days`：范围 0–30days，越高越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| weekly_goal | 越高越好 | ratio | — |
| monthly_goal | 越高越好 | ratio | — |
| yearly_goal | 越高越好 | ratio | — |
| study_goal | 越高越好 | ratio | — |
| fitness_goal | 越高越好 | ratio | — |
| savings_goal | 越高越好 | ratio | — |
| reading_goal | 越高越好 | ratio | — |
| skill_goal | 越高越好 | ratio | — |
| project_goal | 越高越好 | ratio | — |
| health_goal | 越高越好 | ratio | — |
| career_goal | 越高越好 | ratio | — |
| social_goal | 越高越好 | ratio | — |

### leisure

维度模板：`minutes`：范围 0–480minutes，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| games | 越高越好 | minutes | — |
| music | 越高越好 | minutes | — |
| movie | 越高越好 | minutes | — |
| tv | 越高越好 | minutes | — |
| anime | 越高越好 | minutes | — |
| photography | 越高越好 | minutes | — |
| drawing | 越高越好 | minutes | — |
| craft | 越高越好 | minutes | — |
| cooking_fun | 越高越好 | minutes | — |
| puzzle | 越高越好 | minutes | — |
| collecting | 越高越好 | minutes | — |
| diary | 越高越好 | minutes | — |
| garden_fun | 越高越好 | minutes | — |
| pet_fun | 越高越好 | minutes | — |
| travel_fun | 越高越好 | minutes | — |
| fishing | 越高越好 | minutes | — |
| billiards | 越高越好 | minutes | — |
| darts | 越高越好 | minutes | — |

### consumption

维度模板：`amount`：范围 0–5000CNY，越低越好，建议 7 次/窗口；`days`：范围 0–7days，越低越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| delivery_food | 越低越好 | CNY | — |
| bubble_tea | 越低越好 | CNY | — |
| cigarettes | 越低越好 | CNY | — |
| lottery | 越低越好 | CNY | — |
| online_games | 越低越好 | CNY | — |
| livestream_gift | 越低越好 | CNY | — |
| impulse_buy | 越低越好 | CNY | — |
| snack_food | 越低越好 | CNY | — |
| fast_food | 越低越好 | CNY | — |
| alcohol | 越低越好 | CNY | — |
| candy | 越低越好 | CNY | — |
| energy_drink | 越低越好 | CNY | — |

### life_skills

维度模板：`level`：范围 0–10score，越高越好，建议 30 次/窗口；`hours`：范围 0–8hours，越高越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| cooking_skill | 越高越好 | score | — |
| budgeting_skill | 越高越好 | score | — |
| time_management | 越高越好 | score | — |
| negotiation | 越高越好 | score | — |
| first_aid | 越高越好 | score | — |
| navigation | 越高越好 | score | — |
| emergency_prep | 越高越好 | score | — |
| financial_literacy | 越高越好 | score | — |
| digital_literacy | 越高越好 | score | — |
| self_defense | 越高越好 | score | — |
| home_maintenance | 越高越好 | score | — |
| car_maintenance | 越高越好 | score | — |

### personal_growth

维度模板：`score`：范围 0–10score，越高越好，建议 30 次/窗口；`days`：范围 0–30days，越高越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| self_reflection | 越高越好 | score | — |
| feedback_seeking | 越高越好 | score | — |
| challenge_seeking | 越高越好 | score | — |
| comfort_zone | 越高越好 | score | — |
| habit_streak | 越高越好 | score | — |
| journaling_growth | 越高越好 | score | — |
| mentoring | 越高越好 | score | — |
| coaching | 越高越好 | score | — |

### random_misc

维度模板：`value`：范围 0–100score，越高越好，建议 7 次/窗口；`count`：范围 0–100items，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| daily_random | 越高越好 | score | — |
| weekly_random | 越高越好 | score | — |
| monthly_random | 越高越好 | score | — |
