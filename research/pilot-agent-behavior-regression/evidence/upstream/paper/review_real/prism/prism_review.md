# PRISM 四维自评报告（v1.3，LLM-as-judge）

- 论文：`F:\Research\PAPER35_FRONT_DRIFT\main.tex`
- RPC：http://127.0.0.1:11435（HTTP 200）
- 结论：**PASS** —— 四维均 > 6（min=7，短板纪律不平均）

## 维度评分（总分 = min，不平均）

| 维度 | 分 | 评分理由 | 最大弱点 |
|---|---|---|---|
| **P Pertinence**（契合度） | 9 | {
  "score": 9,
  "justification": "论文针对局部LLM系统的代理行为回归测试具有重要性，且与TMLR的目标读者群高度契合，提供了详细的实验和统计结果，填补了现有研究 |  |
| **R Rigor**（严谨性） | 7 | {
  "score": 7,
  "justification": "虽然论文提供了详细的实验设计和统计分析，但在对照组和基线公平性方面没有明确说明，这可能影响结果的可靠性。",
  "top_we |  |
| **I Impact**（贡献量） | 7 | ```json
{"score": 7, "justification": "该工作对社区贡献了一套行为回归测试套件，以及相关的衡量指标，对于评估本地LLM的行为一致性具有重要价值。", "top_w |  |
| **S Sincerity**（诚实性） | 8 | 论文在描述实验结果时较为克制,但对模型之间的行为差异有所夸大,尤其是在工具使用方面的描述。 | 对工具使用行为的描述可能有所夸大。 |

**总分（min）= 7**，最弱维度：R(严谨性)

## 依据句（Sincerity 维度优先人工复核）

- S: tool-use most transferable (BDS 4.48), multilingual most model-specific (BDS 9.42).