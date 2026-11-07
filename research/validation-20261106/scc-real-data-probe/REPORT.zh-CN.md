# semantic-self-consistency 真实数据确定性行为探针

日期：2026-11-07。脚本：`run_probe.py`；校验器：`scripts/verify_scc_real_data_probe.py`。

## 做了什么

- 读取真实公开数据 1941 行：AQuA-RAT 254、SVAMP 1000、StrategyQA test 687。
- 对每行构造 5 个确定性回答场景，每场景 k=10，合计 9705 行场景。
- 场景：全 gold、多数 gold、少数 gold、解析噪声、无答案。
- 方法：first_response、modal、CPW、SCW。
- 所有回答由脚本按 gold 构造，不调用任何模型；`model_used=false`、`paid_api_used=false`。

## 实测

| 环境 | 状态 | problems | exceptions | canonical_sha256 |
|---|---|---:|---:|---|
| local | PASS | 0 | 0 | `4b8a3b251588…` |
| AMD cloud | PASS | 0 | 0 | `4b8a3b251588…` |

两台环境 canonical SHA-256 完全一致，校验器 `gate=PASS`。

## 不变量

- `all_gold_all_methods_recovered`: true
- `majority_gold_modal_recovered`: true
- `minority_gold_modal_not_recovered`: true
- `parse_noise_no_failures`: true
- `no_answer_all_unparsed`: true
- `no_answer_no_method_answered`: true
- `no_exceptions`: true

## 双向变异自测

- 方向 A：把云端回执的 canonical hash 改成全 0，校验器变红 2 个问题。
- 方向 B：把期望行数提高 1，校验器变红 1 个问题。
- 恢复后 base/restored problems=0，`selftest=PASS`。

## 不能声称

- 这不是模型评测：回答是脚本按 gold 构造的，不能当准确率或科研能力分数。
- 这不是论文复现：没有调用 GPT/Llama/Mistral，没有训练，没有 SciBERT/RoBERTa 权重。
- 这不是 PaperBench judge；rubric 叶子仍全部未验证。
- 它只证明在 1941 条真实样本上，解析、众数、CPW/SCW 聚合的确定性行为在本地与云端一致，且异常/契约不变量成立。
