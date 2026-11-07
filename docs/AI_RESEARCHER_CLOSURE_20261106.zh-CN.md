# AI 研究员阶段收尾报告

日期：2026-11-06。状态：本轮工作已完成，代码与证据未提交。

## 结论

1. **可运行能力已经真实落地**：54 条云端轨迹、固定算法/参数空间、
   独立复跑、测试集隔离、哈希回执和 10 类故障注入全部工作。
2. **核心架构判断被实验否定**：在本先导矩阵中，多智能体角色分工没有优于
   单智能体或无反驳基线。
3. **目标噪声被量化**：PeerRead 人工推荐分的 ICC(1,1)=0.124，精确一致率
   30.3%，说明单评审预测本身就是一个高噪声问题。
4. **数据集边界已经封顶**：PeerRead 固定 revision 内论文级可用上限 28 篇；
   RIDAR 全量轨迹 60 条已下载但固定规则检测器三版均未达到 0.5 precision。
5. **当前不能声称**：通用自主科研能力、多智能体增益、rubric 校准、RIDAR
   检测器精度、PaperBench 得分。

## 已验证数字

| 项 | 结果 |
|---|---:|
| 云端轨迹 | 54 |
| 完成 / inconclusive | 44 / 10 |
| 哈希不符 | 0 |
| 独立重跑不一致 | 0 |
| 测试集参与选择 | 0 |
| 模型调用 | 188 |
| Token | 804,272 |
| multi − single 符号检验 | 3/5/2，p=0.73 |
| multi − no_rebuttal 符号检验 | 2/4/4，p=0.69 |
| 故障注入 | 10/10 检出，2/2 对照放行 |
| RIDAR 轨迹 | 60 |
| RIDAR 记录 / acts / spans | 47,797 / 766 / 3,461 |
| PeerRead 固定 revision 可用论文 | 28 |
| PeerRead 去重评审行 | 169 |
| PeerRead ICC(1,1) | 0.124 |
| PeerRead 精确一致率 | 30.3% |
| PeerRead ±1 分一致率 | 74.6% |
| 机器复算门 | 42/42 通过 |

## 关键负结果

- 多智能体角色分工没有显著优势。
- TCE v1 / v2 / v3 固定规则均低于 0.5 precision 下限。
- PeerRead 24 篇 ρ=0.556 在扩展到 28 篇后降至 ρ=0.213，CI 跨 0。
- 6 篇留出集 ρ=0.788 但 p=0.063、CI 跨 0，不能支持校准。
- PaperBench 预检不通过，无 Docker / GPU / 付费 judge 凭据。

## 未完成

- 代码未提交、未推送。
- PaperBench 未执行。
- RIDAR LLM 辅助语义标注未做。
- PeerRead 固定 revision 外的新数据源未引入。
- 没有训练新的科研诚信检测器。

## 下一步决策

1. **提交当前代码与证据**：先把已验证的闭环、报告、脚本和账本入库；
   这是最安全的一步，不新增外部风险。
2. **换 RIDAR 方法**：固定正则已三次失败；下一步需要固定 prompt 的
   LLM 辅助语义标注并重新预注册。
3. **换 PaperBench 环境**：需要 Docker + GPU + 付费 judge 凭据三项授权；
   否则继续报告“未执行”。
4. **扩大 PeerRead**：需要新 revision 或补 PDF，不能沿用当前协议。

## 复现命令

```bash
cd /home/liuzewen/qone-life-work

# 42 项复算门
python3 scripts/verify_research_validation.py \
  --root research/validation-20261106

# PeerRead 可用性
python3 scripts/peerread_availability_census.py \
  --root research/validation-20261106/datasets \
  --out research/validation-20261106/peerread-availability

# PeerRead 评审一致性
python3 scripts/peerread_reviewer_agreement.py \
  --root research/validation-20261106/datasets \
  --out research/validation-20261106/peerread-agreement

# 当前可用测试子集
PYTHONPATH=src .venv/bin/python -m pytest -q \
  --ignore=tests/test_desktop.py \
  --ignore=tests/test_outcomes.py \
  --ignore=tests/test_planner.py \
  --ignore=tests/test_system.py \
  --ignore=tests/test_web.py
```

## 引用口径

对外引用或写进简历时，以
`docs/AI_RESEARCHER_CURRENT_CLAIMS.zh-CN.md` 为准。该文件已合并
PeerRead 目标噪声上限，且明确区分“可写事实”和“不可写结论”。
