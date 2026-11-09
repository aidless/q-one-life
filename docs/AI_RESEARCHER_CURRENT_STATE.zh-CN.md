# Q-One AI 研究员当前状态与下一关

日期：2026-11-07。本文只记录已落盘、可复算的状态。

2026-11-08 续：全 10 任务复现计划的基础设施在
`research/validation-20261108/`，当前 `gate=BLOCKED`（2776 叶全部 blocked、
3 个免费 judge 已锁定但缺逐模型 GO、ImageNet/D4RL 直链 401）。详见
`research/validation-20261108/REPORT.zh-CN.md`。本状态不替代下方 171 项
主验证闸。

2026-11-08 再续：AMD 云端持续负载已跑完 4 个公开视觉模型的 Tiny-ImageNet
扰动矩阵，并补齐 RTP 毒性评分与 4 个公开 D4RL 数据集的 BC 对照；
主验证闸增至 208 项全绿，Full10 仍 `BLOCKED`（3 verified / 22 waived /
2751 blocked）。新增证据和失败诊断见
`research/validation-20261108/REPORT.zh-CN.md`。没有 push、没有付费 API、
没有把公开替代实验写成论文复现。

2026-11-08 用户“同意”后续：官方 judge 仍因缺付费 key、`o3-mini` 与
`chat.completions.parse` 端点而 `BLOCKED`，已写成 5 条逐线 GO 卡；AMD 云端
新增冻结 ResNet-50 特征上的真实线性探针训练（3 epoch、最终验证准确率
0.2955）。主验证闸增至 211 项全绿，Full10 仍 `BLOCKED`。

2026-11-08 “全做”续：修复 full10 密钥扫描器对 shell 变量引用的误报；
把三个真实公开数据叶子交给锁定免费 judge，因第三模型持续分歧而保留 blocked；
AMD 云端完成四模型冻结特征线性探针训练矩阵（4/4、361.62 秒）。continuation
门禁 43 项、主验证闸 213 项全绿，Full10 仍 `BLOCKED` 且叶子状态未变。

## 已完成（有证据）

1. `src/qone_life/research_factory/code_lab.py` 提供有界代码生成、隔离子进程执行和主机隐藏测试；7 项仓库测试通过。
2. `research/validation-20261106/autonomous-code-lab/` 记录一次真实闭环：
   `group/auto-gpt-6` 生成代码 -> 沙盒执行 -> 4/4 隐藏测试通过。产物含代码哈希、执行回执与判定回执。
3. `research/paperbench-submissions/` 下三个 PaperBench dev 任务各有一份带测试的可运行复现包：
   `semantic-self-consistency`（9 测试）、`self-expansion`（9 测试）、
   `self-composing-policies`（9 测试）。三份都是**手写参考实现**，不是模型生成的。
4. `research/validation-20261106/paperbench-smoke/2026-11-07T14-34-31-GMT_run-group_direct_submission_solver/`
   证明三份提交都被 DirectSubmission 归档、dummy judge 正常读取并输出 grade。
5. `scripts/verify_research_validation.py` 现有 171 项机器校验，全绿。
6. `src/qone_life/research_factory/project_lab.py` 新增多文件项目模式；模型生成过
   4 文件项目并通过 pytest + 主机隐藏测试（`autonomous-project-lab/`）。
7. `autonomous-paperbench-loop/` 证明模型生成的项目被 PaperBench DirectSubmission
   归档、dummy judge 成功读取。`generate -> verify -> build -> archive` 闭环已通。
8. `autonomous-full-package/` 证明一份 12 文件完整提交包通过验证、打包、归档与
   dummy judge。3 个核心函数由模型短调用生成，其余模板由宿主补齐；来源边界在
   `qone-full-receipt.json -> source_note` 明确记录。
9. `autonomous-allmodel-core/` 把研究逻辑进一步推进到 6/6 段都由模型短调用生成，
   宿主只拼接与补齐非研究模板文件。验证、打包、归档与 dummy judge 仍全通。
10. `cloud-allmodel-smoke/` 证明该包在已授权 AMD 云端独立 venv 中短执行成功：
    6 项测试通过、入口输出符合预期、文件哈希回传；另经仓库自带 `CloudExecutor`
    正式提交、轮询、取回，状态 `succeeded`、退出码 0。结果已写入决策与命中回执。
    未触碰其他实验目录。
11. `external-task-coverage/` 盘点 10 个选定 PaperBench 任务：10/10 文本与
    rubric 已按 LFS OID 校验，10/10 有可运行提交与 DirectSubmission 归档回执，
    10/10 dummy judge 输出 1.0，0/10 有真实分数；云端统一入口矩阵 10/10 通过，
    合计 48 项短 CPU 测试。另生成 2776 个 rubric 叶子的静态证据合约，
    0 个叶子被标记为已验证。主机隐藏契约闸门在本地与云端均 PASS，
    双向变异自测通过。
12. `datasets/semantic-self-consistency/` 记录 AQuA-RAT 254、SVAMP 1000、
    StrategyQA test 687 的公开来源、下载脚本、SHA-256 与授权边界；
    数据本体不入 git，恢复脚本可重跑并校验。本机与云端数据审计均 PASS，
    1941 行、0 个解析/哈希/行数问题。三个真实文件已接入主提交包，
    加载器、manifest 与隐藏契约测试同步更新。
13. `scc-real-data-probe/` 在 1941 条真实样本 × 5 场景上跑确定性解析/聚合探针；
    本地与云端 canonical hash 一致，双向变异自测通过。没有使用模型或付费 API。
14. `scc-real-model-probe/` 在 AMD 云端用机器上已有的 `Qwen2.5-0.5B-Instruct`
    生成真实回答，接入同一提交包的 top-prob / SC / CPW / SCW，得到第一批可复算
    的真实模型读数。5 批全部验收（StrategyQA / SVAMP / AQuA × 2 提示），
    全部数字由 `summary.raw.jsonl` 重算。详见
    `scc-real-model-probe/REPORT.zh-CN.md`。
15. 同一批回答已用真实 SciBERT / RoBERTa 编码器在 AMD GPU 上重算 CPW / SCW；
    接上语义向量后 instruction 下 StrategyQA 达到 0.55、AQuA 达到 0.40/0.375，
    证明此前低分是 hash embedding 的实现缺口。6 个单元格回执与双向变异自测全绿。
16. `mechanistic-understanding` 从架构桩升级为部分可运行切片：验证过的公开
    Jigsaw `train.csv`（159,571 行）做确定性 90:10 划分，TF-IDF + `softmax(Wx)`
    探针在 15,957 行验证集上实测 0.9595。明确标注这是词袋分类器，不是论文的
    GPT-2 残差流探针；DPO / SVD / PPLM / 真实 judge 仍未复现。
17. `lca-on-the-line` 与 `all-in-one` 各补一组无需大模型/大数据的真实算法切片：
    前者 9 项测试（LCA、信息量、深度、Algorithm 1 CE/BCE 对齐损失），后者 8 项
    测试（VESDE 漂移、扩散、扰动核）。`test-time-model-adaptation` / `rice` /
    `fre` 经盘点仍是架构桩，缺口与所需资源登记在
    `remaining-task-gaps/README.md`，不写空壳冒充实现。
18. 真实 PaperBench judge 的授权与通道已核对：两台机器都没有
    `GRADER_OPENAI_API_KEY`，上游硬断言该变量且默认需要 o3-mini 类
    `chat.completions.parse` 端点；见 `paperbench-real-judge-gate.md`。
    真实 judge 分数仍为 0。
19. `stay-on-topic-with-classifier-free-guidance` 补上 Eq.7 CFG 推理切片：
    可变 gamma、无条件分支从 prompt 最后 token 开始、9 个 benchmark 的官方
    来源契约（全部 `available=false`）；12 项测试通过。未跑 GPT-2/Pythia 与
    9 个数据集的 zero-shot 表格。

## 不能声称

- 三个 dummy score 1.0 是 dummy judge 的固定满分，不是 PaperBench 能力分数。
- 三份提交只覆盖架构、机制、小样本冒烟与指标；没有复现论文表格里的真实数字。
- `self-expansion` 没有跑 CIFAR-100 / ImageNet-R / ImageNet-A / VTAB 上的 5-20 epoch 训练。
- `self-composing-policies` 没有跑 Meta-World / SpaceInvaders / Freeway 上的 10 seed × 1M timestep。
- 没有用真实 PaperBench judge；那需要单独授权与 API key。
- 三个完整复现包仍是手写参考实现；另 7 个任务是架构/接口级最小桩，不覆盖
  各自 rubric 的训练与结果叶子。模型生成过 4 文件最小项目、3 函数辅助包与
  6 段全模型核心逻辑包，但整包中的非研究模板仍由宿主补齐。
- 模型生成项目没有复现论文表格数字，也没有接真实 judge。

## 真正卡在哪里

1. **任务形状残余断层**：已验证 12 文件完整包归档，且 `src/core.py` 的 6 段研究逻辑全部来自模型；
   一次性生成完整多文件包在当前 Magpie 网关下不稳定，长代码 prompt 会挂住。
2. **执行断层**：code lab 是 30 秒本地子进程；真实复现需要 Docker + GPU + 小时级训练。
   本机不是算力节点，长训练必须上云。
3. **判分断层**：目前只有 dummy judge 和自写隐藏测试。没有真实 judge，就没有能力分数。
4. **数据断层**：`semantic-self-consistency` 的三个目标数据已用公开来源、
   哈希与云端审计补齐，并接入主提交包；其余任务仍用采样小文件或架构桩。
5. **闭环残余**：生成、验证、构建、归档已单程打通；自动回填迭代与真实判分还没有接通。

## 下一步（按依赖顺序，可自动化的部分）

1. 扩展 `code_lab`：新增 `project` 模式，让模型生成多文件项目，受同一沙盒契约约束。
2. 已完成：6 段模型逻辑 + 宿主模板 -> 12 文件完整包 -> 隐藏测试 -> 打包 ->
   DirectSubmission + dummy judge；并已由 CloudExecutor 在云端短执行、回填决策。
3. 已完成：10 个选定外部任务的文本、rubric 与提交覆盖盘点。
4. 已完成：另外 7 个任务的可运行架构桩、10 任务 dummy 归档、云端入口矩阵，
   以及 2776 个叶子的证据合约分诊。
   剩余：按合约补真实运行/结果载体；GPU 真实训练、真实 judge 仍需单独 GO。

## 已有命令

```bash
# 本机代码闭环测试
~/.cache/qone-life-venv/bin/python -m pytest -q tests/test_code_lab.py tests/test_code_lab_cli.py

# 三个复现包测试
python3 scripts/verify_research_validation.py --root research/validation-20261106

# 三个 PaperBench dummy judge 归档
cd /tmp/paperbench-upstream/project/paperbench
GRADER_OPENAI_API_KEY=<local-nonempty-placeholder> uv run python -m paperbench.nano.entrypoint \
  paperbench.paper_split=dev \
  paperbench.solver=paperbench.solvers.direct_submission.solver:PBDirectSubmissionSolver \
  paperbench.solver.submissions_dir=/tmp/pb-submissions \
  paperbench.reproduction.skip_reproduction=true \
  paperbench.judge.code_only=true \
  paperbench.judge.scaffold=dummy \
  runner.recorder=nanoeval.json_recorder:json_recorder
```

注意：占位 `GRADER_OPENAI_API_KEY` 只用于通过上游入口的非空校验，不会调用付费模型。
