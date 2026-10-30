# closing_landscape — 送审前诊断（2026-08-12）

**判定：❌ 暂不可送审（soundness blocker：报告数字无法复现）**

## 一、问题

main.tex 报告"真实 API 实验（N=15 within-subjects，DeepSeek-V4-Pro executor + GLM5.2 evaluator）"，
主结果 γ_TV：0.991 → 0.602（CG）→ 0.644（CG+TEE），CV 0.177→0.165→0.159。
但目录内 4 个结果文件数字互不一致，且无法从仓库复现：

| 文件 | standard γ_TV | CG γ_TV | CG+TEE γ_TV | 说明 |
|---|---|---|---|---|
| cg_tee_results.json（07-02） | 0.143 | 0.719 | 0.574 | 仿真初版 |
| cg_tee_checkpoint.json | ~0.12 | ~0.47–0.87 | ~0.72 | 仿真 calibrated |
| **cg_tee_final_results.json**（论文数字来源） | **0.991** | **0.602** | **0.644** | standard 与 real 运行一致，但 CG/TEE 列来源不明 |
| cg_tee_real_results.json（真实 API 运行） | 0.991（与 final 一致） | **全 seed γ=0，H=1.0** | **全 seed γ=0，H=1.0** | CG 条件退化 |

## 二、根因

1. `run_cg_tee.py` 是**仿真脚本**（docstring 明示 simulation-based；TARGET 取自 PAPER-D E4 的 0.991/0.623）。
2. `run_cg_tee_real.py` 是真实 API 脚本，其 CG 条件退化：
   `glm_eval_confidence` 解析失败时**静默回退 0.5** → `(2c-1)=0` → 权重更新恒为零 → 策略分布保持均匀（H=1，γ=0）。
   即真实运行中 CG 的置信度解析基本全部失败。
3. `cg_tee_final_results.json` 的 standard 列 = 真实运行 standard 值；CG/CG+TEE 列既不在 real 运行中（那里是全 0），也不是 run_cg_tee.py 的输出（它写 checkpoint/results 两个文件），git 历史仅有 bulk commit，**来源不可追溯**。

## 三、影响

- 论文主结果（Finding 1/2/3）所依赖的 CG 与 CG+TEE 数字无可靠 provenance → 违反 TMLR Q1（证据支撑声明）与数字可复现硬规则。
- 真实运行的 CG 条件失败意味着"CG 降耦合 39.2%"在现有材料里未被真实实验支持。

## 四、修复方案（本地模型路线，2026-08-12 定）

1. 新建 `run_cg_tee_local.py`：executor + evaluator 全部本地 Ollama（executor=qwen3:4b 或 qwen2.5:7b；evaluator=同族或 deepseek-r1:7b），温度 0。
2. **修复置信度解析**：去掉 0.5 静默回退；解析失败计为 error 并重试；输出中记录解析成功率（送审材料需可审计）。
3. 冒烟：N=3 × R=10，断言三条件 γ 非全 0、H 非全 1、置信度分布有效（无退化）。
4. 全量：N=15 × R=30 × 3 模式 × 4 phase ≈ 21,600 次本地调用（预计 10–20h，后台跑）。
5. 用真实数字回填 main.tex；`cg_tee_final_results.json` 的 CG/TEE 列归档标注 superseded，不可再引用。
6. 重跑后重建 Table + CI + Cohen's d + 重新合规扫描。

## 五、状态

- 当前：**BLOCKED（需机器资源）**——ENWI 20-seed 训练队列占用 100% CPU，重跑待其结束后启动（预计队列完成时间未知，启动后冒烟 30 分钟 + 全量 10–20h）。
- 已登记：接管计划 v2 第 2 条；就绪度档案 closing_landscape 改判"暂不可送审，重跑后复核"。