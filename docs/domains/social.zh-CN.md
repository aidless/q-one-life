# 社交域（social）量化指南

关系、沟通渠道与社群——连接的质量与数量。

> 本文档由 `scripts/generate_domain_docs.py` 从指标目录同源生成，与 `examples/metric-spec.json` 保持一致。

## 指标总览

| 类别 | 指标数 | 方向 | 单位 |
|---|---|---|---|
| relationships | 36 | 越高越好 | hours、score |
| channels | 20 | 越低越好、越高越好 | minutes、times |
| activities | 16 | 越高越好 | minutes |
| communities | 32 | 越高越好 | hours、people |
| **合计** | **104** | | |

## 类别详解

### relationships

维度模板：`hours`：范围 0–8hours，越高越好，建议 7 次/窗口；`quality`：范围 0–10score，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| family | 越高越好 | hours | — |
| parents | 越高越好 | hours | — |
| partner | 越高越好 | hours | — |
| children | 越高越好 | hours | — |
| friends | 越高越好 | hours | — |
| colleagues | 越高越好 | hours | — |
| mentor | 越高越好 | hours | — |
| students | 越高越好 | hours | — |
| clients | 越高越好 | hours | — |
| partners | 越高越好 | hours | — |
| neighbors | 越高越好 | hours | — |
| classmates | 越高越好 | hours | — |
| online_friends | 越高越好 | hours | — |
| hometown_friends | 越高越好 | hours | — |
| coach | 越高越好 | hours | — |
| advisor | 越高越好 | hours | — |
| teammates | 越高越好 | hours | — |
| alumni | 越高越好 | hours | — |

### channels

维度模板：`minutes`：范围 0–240minutes，越低越好，建议 7 次/窗口；`contacts`：范围 0–100times，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| wechat | 越低越好 | minutes | — |
| phone | 越低越好 | minutes | — |
| email | 越低越好 | minutes | — |
| face_to_face | 越低越好 | minutes | — |
| video | 越低越好 | minutes | — |
| sms | 越低越好 | minutes | — |
| voice | 越低越好 | minutes | — |
| forum | 越低越好 | minutes | — |
| community | 越低越好 | minutes | — |
| dm | 越低越好 | minutes | — |

### activities

维度模板：`duration`：范围 0–480minutes，越高越好，建议 7 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| dining | 越高越好 | minutes | — |
| sports | 越高越好 | minutes | — |
| outing | 越高越好 | minutes | — |
| movie | 越高越好 | minutes | — |
| games | 越高越好 | minutes | — |
| tea | 越高越好 | minutes | — |
| coffee | 越高越好 | minutes | — |
| shopping | 越高越好 | minutes | — |
| hiking | 越高越好 | minutes | — |
| camping | 越高越好 | minutes | — |
| concert | 越高越好 | minutes | — |
| exhibition | 越高越好 | minutes | — |
| board_game | 越高越好 | minutes | — |
| escape_room | 越高越好 | minutes | — |
| kayaking | 越高越好 | minutes | — |
| barbecue | 越高越好 | minutes | — |

### communities

维度模板：`hours`：范围 0–8hours，越高越好，建议 7 次/窗口；`members`：范围 0–1000people，越高越好，建议 30 次/窗口。

| 成员 | 方向 | 单位 | 目标 |
|---|---|---|---|
| study_group | 越高越好 | hours | — |
| running_club | 越高越好 | hours | — |
| book_club | 越高越好 | hours | — |
| volunteer | 越高越好 | hours | — |
| church | 越高越好 | hours | — |
| hobby_group | 越高越好 | hours | — |
| online_community | 越高越好 | hours | — |
| gym | 越高越好 | hours | — |
| choir | 越高越好 | hours | — |
| chess_club | 越高越好 | hours | — |
| language_exchange | 越高越好 | hours | — |
| hackathon_team | 越高越好 | hours | — |
| cooking_club | 越高越好 | hours | — |
| photography_group | 越高越好 | hours | — |
| startup_community | 越高越好 | hours | — |
| alumni_assoc | 越高越好 | hours | — |
