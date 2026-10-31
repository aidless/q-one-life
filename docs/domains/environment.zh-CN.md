# 环境域（environment）量化指南

空气、居住舒适、通勤与天气——外部条件的量化窗口。

> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。

## 指标总览

| 类别 | 指标数 | 方向 | 单位 |
|---|---|---|---|
| air_quality | 12 | 越低越好 | index |
| living_comfort | 20 | 目标值、越高越好 | index、score |
| commute | 22 | 越低越好 | minutes、times |
| weather | 20 | 目标值、越高越好 | days、index |
| home | 32 | 越高越好 | minutes、score |
| outdoor | 20 | 越高越好 | minutes、score |
| transport_env | 16 | 越低越好、越高越好 | minutes、score |
| home_comfort | 10 | 越高越好 | score |
| **合计** | **152** | | |

## 类别详解

### air_quality

维度模板：`index`：范围 0–500index，越低越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| pm25 | 越低越好 | index | — |
| pm10 | 越低越好 | index | — |
| o3 | 越低越好 | index | — |
| no2 | 越低越好 | index | — |
| so2 | 越低越好 | index | — |
| co | 越低越好 | index | — |
| co2 | 越低越好 | index | — |
| voc | 越低越好 | index | — |
| formaldehyde | 越低越好 | index | — |
| pollen | 越低越好 | index | — |
| radon | 越低越好 | index | — |
| asbestos | 越低越好 | index | — |

### living_comfort

维度模板：`value`：范围 0–1000index，目标值，建议 7 次/窗口；`comfort`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| temperature | 目标值 | index | 22 |
| humidity | 目标值 | index | 50 |
| noise | 目标值 | index | 30 |
| illuminance | 目标值 | index | 500 |
| airflow | 目标值 | index | 50 |
| dust | 目标值 | index | 20 |
| mold | 目标值 | index | 10 |
| emf | 目标值 | index | 20 |
| odor | 目标值 | index | 10 |
| vibration | 目标值 | index | 10 |

### commute

维度模板：`minutes`：范围 0–180minutes，越低越好，建议 7 次/窗口；`times`：范围 0–30times，越低越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| subway | 越低越好 | minutes | — |
| bus | 越低越好 | minutes | — |
| walk | 越低越好 | minutes | — |
| cycling | 越低越好 | minutes | — |
| driving | 越低越好 | minutes | — |
| taxi | 越低越好 | minutes | — |
| shared_bike | 越低越好 | minutes | — |
| high_speed_rail | 越低越好 | minutes | — |
| flight | 越低越好 | minutes | — |
| ferry | 越低越好 | minutes | — |
| tram | 越低越好 | minutes | — |

### weather

维度模板：`value`：范围 0–1100index，目标值，建议 7 次/窗口；`days`：范围 0–7days，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| temperature_c | 目标值 | index | 22 |
| humidity_pct | 目标值 | index | 50 |
| wind_kmh | 目标值 | index | 15 |
| rain_mm | 目标值 | index | 2 |
| snow_cm | 越低越好 | — | 0 |
| sun_hours | 目标值 | index | 6 |
| uv_index | 目标值 | index | 3 |
| visibility_km | 目标值 | index | 10 |
| pressure_hpa | 目标值 | index | 1013 |
| air_quality | 目标值 | index | 50 |

### home

维度模板：`minutes`：范围 0–240minutes，越高越好，建议 7 次/窗口；`quality`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| cleaning | 越高越好 | minutes | — |
| cooking | 越高越好 | minutes | — |
| laundry | 越高越好 | minutes | — |
| dishes | 越高越好 | minutes | — |
| gardening | 越高越好 | minutes | — |
| repair | 越高越好 | minutes | — |
| organizing | 越高越好 | minutes | — |
| decluttering | 越高越好 | minutes | — |
| waste_recycling | 越高越好 | minutes | — |
| plant_care | 越高越好 | minutes | — |
| pet_care | 越高越好 | minutes | — |
| grocery | 越高越好 | minutes | — |
| errand | 越高越好 | minutes | — |
| budgeting_work | 越高越好 | minutes | — |
| caring | 越高越好 | minutes | — |
| mail | 越高越好 | minutes | — |

### outdoor

维度模板：`minutes`：范围 0–480minutes，越高越好，建议 7 次/窗口；`quality`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| park_walk | 越高越好 | minutes | — |
| city_walk | 越高越好 | minutes | — |
| nature_hike | 越高越好 | minutes | — |
| rooftop | 越高越好 | minutes | — |
| balcony | 越高越好 | minutes | — |
| waterfront | 越高越好 | minutes | — |
| trail_run | 越高越好 | minutes | — |
| camping_trip | 越高越好 | minutes | — |
| picnic | 越高越好 | minutes | — |
| garden_work | 越高越好 | minutes | — |

### transport_env

维度模板：`minutes`：范围 0–240minutes，越低越好，建议 7 次/窗口；`quality`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| commute_crowd | 越低越好 | minutes | — |
| traffic | 越低越好 | minutes | — |
| waiting | 越低越好 | minutes | — |
| transfer | 越低越好 | minutes | — |
| walking_route | 越低越好 | minutes | — |
| bike_route | 越低越好 | minutes | — |
| public_transit | 越低越好 | minutes | — |
| car_dependency | 越低越好 | minutes | — |

### home_comfort

维度模板：`quality`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| air_quality_home | 越高越好 | score | — |
| lighting | 越高越好 | score | — |
| acoustic | 越高越好 | score | — |
| thermal | 越高越好 | score | — |
| ergonomic | 越高越好 | score | — |
| storage | 越高越好 | score | — |
| decor | 越高越好 | score | — |
| cleanliness | 越高越好 | score | — |
| plants | 越高越好 | score | — |
| safety | 越高越好 | score | — |
