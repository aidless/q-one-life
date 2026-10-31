# 财务域（finance）量化指南

支出、收入、资产与债务——每日记账到月度财务健康，方向感知打分。

> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。

## 指标总览

| 类别 | 指标数 | 方向 | 单位 |
|---|---|---|---|
| expenses | 64 | 越低越好 | CNY、days |
| income | 32 | 越高越好 | CNY、months |
| assets | 30 | 越高越好 | CNY、ratio |
| debts | 10 | 越低越好 | CNY |
| budget_lines | 36 | 目标值、越低越好 | CNY |
| **合计** | **172** | | |

## 类别详解

### expenses

维度模板：`daily_amount`：范围 0–1000CNY，越低越好，建议 7 次/窗口；`weekly_days`：范围 0–7days，越低越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| dining | 越低越好 | CNY | — |
| transport | 越低越好 | CNY | — |
| housing | 越低越好 | CNY | — |
| utilities | 越低越好 | CNY | — |
| telecom | 越低越好 | CNY | — |
| entertainment | 越低越好 | CNY | — |
| education | 越低越好 | CNY | — |
| medical | 越低越好 | CNY | — |
| clothing | 越低越好 | CNY | — |
| daily_goods | 越低越好 | CNY | — |
| travel | 越低越好 | CNY | — |
| pets | 越低越好 | CNY | — |
| insurance | 越低越好 | CNY | — |
| taxes | 越低越好 | CNY | — |
| gifts | 越低越好 | CNY | — |
| repairs | 越低越好 | CNY | — |
| beauty | 越低越好 | CNY | — |
| fitness | 越低越好 | CNY | — |
| books | 越低越好 | CNY | — |
| stationery | 越低越好 | CNY | — |
| express | 越低越好 | CNY | — |
| housekeeping | 越低越好 | CNY | — |
| medicine | 越低越好 | CNY | — |
| smoking | 越低越好 | CNY | — |
| coffee | 越低越好 | CNY | — |
| takeout | 越低越好 | CNY | — |
| taxi | 越低越好 | CNY | — |
| rent | 越低越好 | CNY | — |
| mortgage | 越低越好 | CNY | — |
| subscriptions | 越低越好 | CNY | — |
| snacks | 越低越好 | CNY | — |
| charity | 越低越好 | CNY | — |

### income

维度模板：`monthly_amount`：范围 0–100000CNY，越高越好，建议 30 次/窗口；`months`：范围 0–12months，越高越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| salary | 越高越好 | CNY | — |
| bonus | 越高越好 | CNY | — |
| part_time | 越高越好 | CNY | — |
| investment | 越高越好 | CNY | — |
| rental | 越高越好 | CNY | — |
| royalty | 越高越好 | CNY | — |
| dividend | 越高越好 | CNY | — |
| interest | 越高越好 | CNY | — |
| subsidy | 越高越好 | CNY | — |
| reimbursement | 越高越好 | CNY | — |
| writing_fee | 越高越好 | CNY | — |
| teaching | 越高越好 | CNY | — |
| consulting | 越高越好 | CNY | — |
| outsourcing | 越高越好 | CNY | — |
| cashback | 越高越好 | CNY | — |
| grant | 越高越好 | CNY | — |

### assets

维度模板：`amount`：范围 0–10000000CNY，越高越好，建议 30 次/窗口；`allocation`：范围 0–1ratio，越高越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| cash | 越高越好 | CNY | — |
| demand_deposit | 越高越好 | CNY | — |
| fixed_deposit | 越高越好 | CNY | — |
| money_fund | 越高越好 | CNY | — |
| bond_fund | 越高越好 | CNY | — |
| stock_fund | 越高越好 | CNY | — |
| index_fund | 越高越好 | CNY | — |
| stock | 越高越好 | CNY | — |
| bond | 越高越好 | CNY | — |
| real_estate | 越高越好 | CNY | — |
| gold | 越高越好 | CNY | — |
| bitcoin | 越高越好 | CNY | — |
| pension | 越高越好 | CNY | — |
| housing_fund | 越高越好 | CNY | — |
| precious_metal | 越高越好 | CNY | — |

### debts

维度模板：`balance`：范围 0–10000000CNY，越低越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| credit_card | 越低越好 | CNY | — |
| mortgage | 越低越好 | CNY | — |
| car_loan | 越低越好 | CNY | — |
| consumer_loan | 越低越好 | CNY | — |
| huabei | 越低越好 | CNY | — |
| jiedai | 越低越好 | CNY | — |
| baitiao | 越低越好 | CNY | — |
| student_loan | 越低越好 | CNY | — |
| pawn | 越低越好 | CNY | — |
| campus_loan | 越低越好 | CNY | — |

### budget_lines

维度模板：`budget`：范围 0–100000CNY，目标值，建议 30 次/窗口；`actual`：范围 0–100000CNY，越低越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| dining_budget | 目标值 | CNY | 2000 |
| transport_budget | 目标值 | CNY | 500 |
| entertainment_budget | 目标值 | CNY | 500 |
| education_budget | 目标值 | CNY | 1000 |
| housing_budget | 目标值 | CNY | 3000 |
| utilities_budget | 目标值 | CNY | 500 |
| medical_budget | 目标值 | CNY | 300 |
| clothing_budget | 目标值 | CNY | 300 |
| travel_budget | 目标值 | CNY | 1000 |
| misc_budget | 目标值 | CNY | 500 |
| daily_goods_budget | 目标值 | CNY | 500 |
| fitness_budget | 目标值 | CNY | 200 |
| subs_budget | 目标值 | CNY | 100 |
| gift_budget | 目标值 | CNY | 200 |
| pet_budget | 目标值 | CNY | 300 |
| telecom_budget | 目标值 | CNY | 150 |
| repairs_budget | 目标值 | CNY | 300 |
| beauty_budget | 目标值 | CNY | 200 |
