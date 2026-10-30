# CLAIM_LEDGER.md

本账本覆盖当前匿名稿摘要、引言、方法、结果和结论中的可核验主张。数值均锚定到证据包；无法由现有证据独立确认的机制性表述标记为 `inconclusive`，正文必须使用限定语。

| ID | 声明（章节） | 证据文件+字段 | 数值 | 如何验证 | 状态 |
|---|---|---|---|---|---|
| C01 | DeepSeek V4-Chat 长度注入网格每个 cell 使用 10 个配对种子；分析文件包含 9 个架构对比。 | evidence/analyses/r1_dose_response_contrasts.json -> contrasts[0].n_seeds | 10 | 逐记录计数；contrast 数组长度独立核对为 9 | verified |
| C02 | DeepSeek V4-Chat 在 p=0.2 时 RAG 相对 Append-Only 的点估计降低约 27.9%，配对效应 d_z=0.96；经 k=9 校正不显著。 | evidence/analyses/r1_dose_response_contrasts.json -> contrasts[0].mean_diff_a_minus_b / contrasts[0].d_z / contrasts[0].p_holm_k9 | 0.1171 / 0.9645 / 0.1104 | 从 per-seed gamma 差值重算；检查方向与校正 | verified |
| C03 | DeepSeek V4-Chat 在 p=0.8 时 Summarization 相对 Append-Only 的点估计降低约 27.3%，d_z=1.178，raw p=0.0047，Bonferroni(k=9) p_adj=0.043。 | evidence/analyses/r1_dose_response_contrasts.json -> contrasts[7].mean_diff_a_minus_b / contrasts[7].d_z / contrasts[7].p_raw | 0.0727 / 1.178 / 0.0047 | 独立重算配对 t 检验和 min(1,9p)=0.0423（正文四舍五入为 0.043） | verified |
| C04 | Qwen3.7-Plus p=0.8 authority arm 的 Summarization 点估计为 0.544，Append-Only 为 0.802；该臂仅作描述性分析。 | evidence/recomputed_cell_means_FIXED.json -> qwen3.7-plus-Summarization-authority-p0.8.mean / qwen3.7-plus-Append-Only-authority-p0.8.mean | 0.543864189478 / 0.801762864464 | 核对 10-seed均值及正文表格 | verified |
| C05 | Qwen 与 Round-1 V4-Chat 的架构排序可能依赖模型/版本；第三模型方向文件记录 R1 Summ-lower、Round-4 deepseek-v4-pro/flash Summ-higher。 | evidence/analyses/p5_third_model_direction_20260809.json -> rows | diff -0.0727, -0.0969, 0.0007, 0.2024 | 核对各模型方向与 n；不作普适因果断言 | verified |
| C06 | Round-4 完整两模型 factorial 含 36 cells、每 cell n=30，schema 校验通过。 | evidence/analyses/round4_validation_20260808.json -> files / cells / schema_ok | 1080 / 36 / true | 校验归档文件计数和 schema | verified |
| C07 | Round-4 在 deepseek-v4-pro 与 deepseek-v4-flash 上 Summarization 为最高 Gamma，方向与 R1 V4-Chat 相反。 | evidence/analyses/round4_validation_20260808.json -> r1_contrast_replication | 方向记录 | 由 per_cell_mean 和 replication 字段核对 | verified |
| C08 | authority-marker arm 不能单独区分 authority uptake 与一般输出长度/格式/任务难度变化。 | evidence/analyses/p5_external_task_20260809.json -> [0].gamma / [1].gamma | 外部任务 Gamma 仅作构念审计 | 检查外部任务与 authority endpoint 不同；不推断机制 | inconclusive |
| C09 | RAG 阈值 theta=0.1 来自 5-seed sweep，而非测试集调参。 | evidence/protocol.md | theta=0.1; 5 seeds | 核对预注册协议与 sweep 记录 | verified |
| C10 | Qwen authority-marker 注入率在三架构间约为 0.80/0.80/0.72，说明注入保真度较高但不等于偏差传播。 | evidence/p5_grid_v4flash_20260807.json -> cells["authority|Append-Only|p0.8"].n / cells["authority|Summarization|p0.8"].n | n=10 | 结合 judge 输出与表格；机制解释保持限定 | inconclusive |
| C11 | 研究结论限定为：在测试的模型、任务、污染协议和输出长度端点内，架构排序会变化；不声称某架构普遍最优。 | evidence/analyses/round4_validation_20260808.json -> cells | scope only | 复核实验设计和限制段落 | verified |
| C12 | 所有确认性 pairwise 比较采用同一 cell 内 per-seed paired t-test，并进行家族级多重比较校正。 | evidence/analyses/r1_dose_response_contrasts.json -> method | paired t-test; Bonferroni/Holm/BH | 复核分析脚本与 contrasts 字段 | verified |

## 强断言审计

| 断言 | 证据支持 | 处理 |
|---|---|---|
| “first systematic comparison” | 仅有文献检索与当前工作范围 | 保留“to our knowledge”，避免绝对优先权 |
| “no architecture uniformly best” | 多模型/版本方向不一致 | 保留，限定为测试集合 |
| authority bias 被传播/机制由 summarization 导致 | 当前 endpoint 不能识别机制 | 不作强断言；C08/C10 标记 inconclusive 并使用 hedge |
