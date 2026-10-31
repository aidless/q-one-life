# 健康域（health）量化指南

身体状态、营养摄入、运动与睡眠——可观察、可记录、可打分的健康维度。

> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。

## 指标总览

| 类别 | 指标数 | 方向 | 单位 |
|---|---|---|---|
| vitamins_minerals | 54 | 越高越好 | days、mg |
| vitals | 15 | 目标值 | — |
| exercise | 44 | 越高越好 | minutes、times |
| body_parts | 12 | 越高越好 | minutes |
| food_groups | 22 | 越高越好 | servings |
| sleeping | 15 | 目标值 | hours |
| **合计** | **162** | | |

## 类别详解

### vitamins_minerals

维度模板：`intake`：范围 0–2000mg，越高越好，建议 7 次/窗口；`days`：范围 0–7days，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| vitamin_a | 越高越好 | mg | — |
| vitamin_c | 越高越好 | mg | — |
| vitamin_d | 越高越好 | mg | — |
| vitamin_e | 越高越好 | mg | — |
| vitamin_k | 越高越好 | mg | — |
| vitamin_b1 | 越高越好 | mg | — |
| vitamin_b2 | 越高越好 | mg | — |
| vitamin_b3 | 越高越好 | mg | — |
| vitamin_b5 | 越高越好 | mg | — |
| vitamin_b6 | 越高越好 | mg | — |
| vitamin_b9 | 越高越好 | mg | — |
| vitamin_b12 | 越高越好 | mg | — |
| calcium | 越高越好 | mg | — |
| iron | 越高越好 | mg | — |
| zinc | 越高越好 | mg | — |
| magnesium | 越高越好 | mg | — |
| potassium | 越高越好 | mg | — |
| sodium | 越高越好 | mg | — |
| selenium | 越高越好 | mg | — |
| iodine | 越高越好 | mg | — |
| copper | 越高越好 | mg | — |
| manganese | 越高越好 | mg | — |
| chromium | 越高越好 | mg | — |
| phosphorus | 越高越好 | mg | — |
| folate | 越高越好 | mg | — |
| choline | 越高越好 | mg | — |
| biotin | 越高越好 | mg | — |

### vitals

维度模板：`value`：范围 0–200(成员级单位)，目标值，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| systolic | 目标值 | mmHg | 120 |
| diastolic | 目标值 | mmHg | 80 |
| resting_heart_rate | 目标值 | bpm | 65 |
| blood_glucose | 目标值 | mg/dL | 90 |
| body_temperature | 目标值 | degC | 36.5 |
| blood_oxygen | 目标值 | pct | 98 |
| respiratory_rate | 目标值 | breaths | 16 |
| waist_circumference | 目标值 | cm | 80 |
| hip_circumference | 目标值 | cm | 95 |
| bmi | 目标值 | kg/m2 | 22 |
| body_fat | 目标值 | pct | 20 |
| muscle_mass | 目标值 | kg | 40 |
| bone_mass | 目标值 | kg | 2.5 |
| body_water | 目标值 | pct | 60 |
| visceral_fat | 目标值 | index | 8 |

### exercise

维度模板：`minutes`：范围 0–300minutes，越高越好，建议 7 次/窗口；`sessions`：范围 0–14times，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| running | 越高越好 | minutes | — |
| walking | 越高越好 | minutes | — |
| cycling | 越高越好 | minutes | — |
| swimming | 越高越好 | minutes | — |
| strength_training | 越高越好 | minutes | — |
| yoga | 越高越好 | minutes | — |
| stretching | 越高越好 | minutes | — |
| hiit | 越高越好 | minutes | — |
| jump_rope | 越高越好 | minutes | — |
| rowing | 越高越好 | minutes | — |
| hiking | 越高越好 | minutes | — |
| pilates | 越高越好 | minutes | — |
| boxing | 越高越好 | minutes | — |
| dancing | 越高越好 | minutes | — |
| badminton | 越高越好 | minutes | — |
| tennis | 越高越好 | minutes | — |
| basketball | 越高越好 | minutes | — |
| football | 越高越好 | minutes | — |
| climbing | 越高越好 | minutes | — |
| skating | 越高越好 | minutes | — |
| golf | 越高越好 | minutes | — |
| table_tennis | 越高越好 | minutes | — |

### body_parts

维度模板：`minutes`：范围 0–120minutes，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| neck | 越高越好 | minutes | — |
| shoulders | 越高越好 | minutes | — |
| lower_back | 越高越好 | minutes | — |
| wrists | 越高越好 | minutes | — |
| eyes | 越高越好 | minutes | — |
| knees | 越高越好 | minutes | — |
| hips | 越高越好 | minutes | — |
| ankles | 越高越好 | minutes | — |
| head | 越高越好 | minutes | — |
| abdomen | 越高越好 | minutes | — |
| feet | 越高越好 | minutes | — |
| elbows | 越高越好 | minutes | — |

### food_groups

维度模板：`servings`：范围 0–12servings，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| grains | 越高越好 | servings | — |
| vegetables | 越高越好 | servings | — |
| fruits | 越高越好 | servings | — |
| protein | 越高越好 | servings | — |
| dairy | 越高越好 | servings | — |
| legumes | 越高越好 | servings | — |
| nuts | 越高越好 | servings | — |
| oils | 越高越好 | servings | — |
| water | 越高越好 | servings | — |
| whole_grain | 越高越好 | servings | — |
| seafood | 越高越好 | servings | — |
| eggs | 越高越好 | servings | — |
| mushrooms | 越高越好 | servings | — |
| soy | 越高越好 | servings | — |
| herbs | 越高越好 | servings | — |
| fermented | 越高越好 | servings | — |
| dark_leafy | 越高越好 | servings | — |
| berries | 越高越好 | servings | — |
| citrus | 越高越好 | servings | — |
| whole_foods | 越高越好 | servings | — |
| processed_food | 越高越好 | servings | — |
| sugary_drink | 越高越好 | servings | — |

### sleeping

维度模板：`hours`：范围 0–24hours，目标值，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| night_sleep | 目标值 | hours | 8 |
| afternoon_nap | 目标值 | hours | 0.5 |
| time_to_fall_asleep | 目标值 | hours | 0.25 |
| time_in_bed | 目标值 | hours | 8 |
| night_wakeups | 目标值 | hours | 1 |
| bedtime | 目标值 | hours | 23 |
| wake_time | 目标值 | hours | 7 |
| sleep_quality | 目标值 | hours | 8 |
| deep_sleep | 目标值 | hours | 1.5 |
| rem_sleep | 目标值 | hours | 2 |
| light_sleep | 目标值 | hours | 4.5 |
| sleep_regularity | 目标值 | hours | 0.8 |
| sleep_environment_score | 目标值 | hours | 8 |
| mattress_score | 目标值 | hours | 7 |
| pillow_score | 目标值 | hours | 7 |
