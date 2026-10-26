# Q-One Life 0.6 使用与验收说明

本版接入可训练的人生状态与决策内核。详细设计见 [core内核文档](https://github.com/aidless/q-one-core/blob/main/docs/LIFE_KERNEL.zh-CN.md)，[技术进阶蓝图](https://github.com/aidless/q-one-core/blob/main/docs/ADVANCED_ROADMAP.zh-CN.md)。

## 使用入口

安装并启动应用：

```bash
bash scripts/setup.sh
bash scripts/run.sh
```

打开页面的设置，选择“查看或导入人生模型”。导入文件包含观察口径、价值与目标取舍、资源预算、行动及可选的历史学习记录。首次导入前没有人生模型，应用继续使用原来的基础目标规划。

仓库的 `examples/adaptive.synthetic.json` 是合成体验文件，**不包含你的个人数据**。示例时间固定为2026-10-25，资源有效窗只有当天；过期后拒绝以旧预算推荐属于预期行为。真实使用时应按实际日期、实际资源和实际观察建立新模型，不能只修改日期冒充新的真实记录。

体验建议使用独立目录：

```bash
runtime="$HOME/.local/share/q-one-runtime/venv/bin/qone-life"
"$runtime" system-import --file examples/adaptive.synthetic.json --home /tmp/q-one-adaptive-example
QONE_DEMO=1 "$runtime" serve --home /tmp/q-one-adaptive-example --port 8768
```

也可以检查固定时点的示例推演，无需调用语言模型：

```bash
"$runtime" system-inspect --home /tmp/q-one-adaptive-example --as-of 2026-10-25T00:00:00Z
"$runtime" system-inspect --home /tmp/q-one-adaptive-example --replay
```

更新模型文件时，`system-import` 需要 `--parent-revision 当前版本ID`，防止覆盖并发更新。网页导入会自动携带读取时的版本。0.7版可以在观察页登记数量观察和明确确认的行动结果，自动关联已有事前证据；待办勾选本身仍不能变成训练标签。[操作流程与限制](OUTCOME_INTAKE.zh-CN.md)。

## 首页的行为变化

- 有足够支持的历史：显示“个人历史预测”，依据目标取舍与资源比较给出有条件行动提案。
- 只声明了影响假设：显示“显式假设推演”，不伪装成已学习的效果。
- 数据不足、预测范围重叠或取舍未声明：保留方案和缺失条件，不悄悄回退到大模型猜测。
- 采纳后：形成任务，保存预测收据，按资源窗口记录完整承诺；完成任务不会退还已经安排的资源，也不会被当作效果标签。
- 当天已采纳或跳过的行动不重复推荐；模型版本变化后仍保留当天已承诺资源。
- 未配置人生模型：继续基础目标规划；现有完整任务不允许被模型改短以凑预算，需要用户先明确拆分。

应用每分钟形成稳定的评估时点，因此预算刚过期或观察刚过期的变化可能在下一分钟反映。采纳前重新评估并校验提案哈希；模型或预算变化后旧提案会被拒绝。

## 模型文件结构

```text
schema_version: 1
 title
 dimensions[]       可配置维度，可带parent_id
 values[]           用户明确声明的价值
 measures[]         定义、单位、量表、有效期
 observations[]     发生时间、登记时间、来源、更正引用
 resources[]        预算、单位、有效时间窗
 goals[]            条件、目标树、价值引用
 goal_order[]       用户声明的完整目标顺序
 hypotheses[]       影响假设及来源
 actions[]          完整耗时、前置、成本、影响、验收
 guardrails[]       明确底线
 learning           可选：固定窗口、特征、结果、先验、样本门槛
 episodes[]         可选：执行记录与前后观察ID
```

完整字段和量表语义以core文档及校验器为准。行动效果、主观感受、设备记录不能互相冒充。当前没有通用“人生总分”，也没有为未分类指标默认加权。

## 本地接口

| 接口 | 用途 |
|---|---|
| `GET /api/system` | 当前模型及版本 |
| `POST /api/system` | 校验并增加版本；`{model,parent_revision}` |
| `POST /api/system/evaluate` | 固定时点比较；可指定as_of、available_minutes、max_actions、horizon_days |
| `POST /api/system/replay` | 只使用当时已知结果的历史预测回放 |
| `GET /api/planner` | 首页自动推荐、状态、资源与方案证据 |
| `POST /api/planner/{id}/feedback` | 采纳或跳过，必须带当前proposal_sha256 |
| `GET /api/backup` | v3私有备份，包含模型版本与承诺 |

写接口沿用本地客户端、同源和JSON约束。模型文件和私有备份包含原始个人信息；不会自动上传到开源仓库。训练与规划在本机运行，新内核不自动请求远程模型。

## 已验证与尚未验证

本地验收覆盖：真实内核经过API导入和推荐；采纳与资源保留；重启；并发重复采纳；过期提案；模型版本冲突；备份版本链与内容校验；v1/v2/v3兼容；历史回放与完整任务预算。

这些是工程检查。合成示例的预测优于保持不变基线，只说明在生成器指定机制下链路可训练、可重放。尚无真实个人数据的预测效果、真实推荐收益或因果证据。

局限：只支持有限当前行动组合和固定预测窗口；没有长期潜在世界模型、连续时间调度器、自动因果发现或安全探索策略。涉及学习结果的过程底线不能验证时，系统拒绝自动选择。下一阶段应先建立真实个人模型与持续观察流程，再决定更深的时序模型。

## 0.6：在线校准候选的影子评测

系统增加了按时间回放的校准对照入口。它读取当前模型的历史记录，比较候选预测范围，**不会保存模型版本、改变推荐区间或产生任务**。候选在稳定合成场景改善，但未通过均值突变和噪声增大场景的采用条件；目前不进入默认推荐。

```bash
"$runtime" system-inspect --home /tmp/q-one-adaptive-example --replay --calibration-shadow
```

本地接口 `POST /api/system/replay` 支持：

```json
{"candidate_calibration":{"method":"prequential_aci","step_size":0.01,"window":64,"min_samples":10}}
```

结果标记 `purpose=shadow_interval_evaluation`、`used_for_recommendations=false`。同时报告有限区间数量、拒绝数量、经验覆盖、平均宽度和区间评分；密度评分仍对应原始Student-t分布。范围收窄不能单独作为采用理由，也不能把原内核在突变场景中的漏覆盖隐藏掉。

[完整对照与采用决定](https://github.com/aidless/q-one-core/blob/main/docs/CALIBRATION_EVALUATION.zh-CN.md)包含固定协议、官方来源和负面结果。当前没有真实个人效果或覆盖保证。
