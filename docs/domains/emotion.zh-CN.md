# 情绪域（emotion）量化指南

情绪状态、压力源与自我意象——主观感受的如实记录。

> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。

## 指标总览

| 类别 | 指标数 | 方向 | 单位 |
|---|---|---|---|
| panas | 20 | 越高越好 | score |
| moods | 36 | 越低越好、越高越好 | days、score |
| stressors | 17 | 越低越好 | score |
| self_image | 18 | 越高越好 | score |
| **合计** | **91** | | |

## 类别详解

### panas

维度模板：`score`：范围 1–5score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| interested | 越高越好 | score | — |
| alert | 越高越好 | score | — |
| excited | 越高越好 | score | — |
| enthusiastic | 越高越好 | score | — |
| inspired | 越高越好 | score | — |
| determined | 越高越好 | score | — |
| attentive | 越高越好 | score | — |
| active | 越高越好 | score | — |
| proud | 越高越好 | score | — |
| strong | 越高越好 | score | — |
| afraid | 越高越好 | score | — |
| hostile | 越高越好 | score | — |
| guilty | 越高越好 | score | — |
| ashamed | 越高越好 | score | — |
| upset | 越高越好 | score | — |
| irritable | 越高越好 | score | — |
| anxious | 越高越好 | score | — |
| jittery | 越高越好 | score | — |
| nervous | 越高越好 | score | — |
| scared | 越高越好 | score | — |

### moods

维度模板：`score`：范围 0–10score，越高越好，建议 7 次/窗口；`frequency`：范围 0–7days，越低越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| happy | 越高越好 | score | — |
| calm | 越高越好 | score | — |
| content | 越高越好 | score | — |
| grateful | 越高越好 | score | — |
| hopeful | 越高越好 | score | — |
| optimistic | 越高越好 | score | — |
| fearful | 越高越好 | score | — |
| stressed | 越高越好 | score | — |
| tired | 越高越好 | score | — |
| lonely | 越高越好 | score | — |
| angry | 越高越好 | score | — |
| sad | 越高越好 | score | — |
| bored | 越高越好 | score | — |
| jealous | 越高越好 | score | — |
| remorseful | 越高越好 | score | — |
| disgusted | 越高越好 | score | — |
| cheerful | 越高越好 | score | — |
| satisfied | 越高越好 | score | — |

### stressors

维度模板：`severity`：范围 0–10score，越低越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| work | 越低越好 | score | — |
| finance | 越低越好 | score | — |
| health | 越低越好 | score | — |
| relationship | 越低越好 | score | — |
| family | 越低越好 | score | — |
| environment | 越低越好 | score | — |
| academic | 越低越好 | score | — |
| social | 越低越好 | score | — |
| sleep | 越低越好 | score | — |
| time_pressure | 越低越好 | score | — |
| responsibility | 越低越好 | score | — |
| uncertainty | 越低越好 | score | — |
| conflict | 越低越好 | score | — |
| deadline | 越低越好 | score | — |
| relocation | 越低越好 | score | — |
| noise | 越低越好 | score | — |
| procrastination | 越低越好 | score | — |

### self_image

维度模板：`score`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| confidence | 越高越好 | score | — |
| self_esteem | 越高越好 | score | — |
| body_image | 越高越好 | score | — |
| self_worth | 越高越好 | score | — |
| resilience | 越高越好 | score | — |
| optimism | 越高越好 | score | — |
| purpose | 越高越好 | score | — |
| meaning | 越高越好 | score | — |
| identity | 越高越好 | score | — |
| self_efficacy | 越高越好 | score | — |
| self_compassion | 越高越好 | score | — |
| growth_mindset | 越高越好 | score | — |
| self_awareness | 越高越好 | score | — |
| assertiveness | 越高越好 | score | — |
| gratitude | 越高越好 | score | — |
| forgiveness | 越高越好 | score | — |
| patience | 越高越好 | score | — |
| curiosity | 越高越好 | score | — |
