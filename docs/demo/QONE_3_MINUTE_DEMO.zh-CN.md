# Q-One 三分钟演示脚本

## 演示定位

这不是“AI 自动替人做决定”的演示，而是：

> 一个本地优先的个人决策 Agent：没有模型也能完成闭环；启用模型后仍保留候选 ID、输入摘要和推荐哈希；证据不足时明确回退或拒绝发布。

演示只使用真实 Electron、真实 Python sidecar 和固定哈希的 Qwen3-0.6B。未签名安装包、三平台正式发布和论文录用不作为演示结论。

## 录制前检查

```bash
cd desktop
pnpm install --frozen-lockfile
node node_modules/electron/install.js
pnpm test
```

严格演示需要提供已经构建的 sidecar 和已校验模型：

```bash
export QONE_SIDECAR_BIN=/absolute/path/to/qone-life-sidecar
export QONE_E2E_LOCAL_MODEL_PATH=/absolute/path/to/Qwen3-0.6B-Q8_0.gguf
export QONE_REQUIRE_LOCAL_MODEL_E2E=1
export QONE_CAPTURE_DEMO=1
export QONE_DEMO_OUTPUT=/absolute/path/to/artifacts/resume-kit/demo
pnpm run test:e2e -- e2e/capture-demo.spec.ts
```

截图必须来自这次真实运行，不手绘界面，不使用合成截图冒充本地模型输出。

## 三分钟分镜

| 时间 | 画面 | 口播重点 |
|---|---|---|
| 0:00–0:20 | 问题页或架构图 | 个人 Agent 最大的问题不是“会不会生成建议”，而是建议是否绑定输入、能否复现、失败后能否恢复。 |
| 0:20–0:45 | 架构图 | Electron 只暴露最小 preload API；Python sidecar 只监听随机回环端口；所有 API 都要求一次性 capability。 |
| 0:45–1:20 | `01-first-run.png` | 首次启动只问语言和目标；备份、模型均可跳过。没有模型时规则推荐仍能完成闭环。 |
| 1:20–1:55 | `02-today-recommendation.png` | 展示行动、第一步、完成标准、预计时间和依据。口播中明确指出：推荐不是行动成功概率。 |
| 1:55–2:20 | `03-completed-action.png` + `04-review.png` | 采纳只是创建一个任务，完成和复盘是另外的显式动作；系统不会把“采纳建议”当成“产生结果”。 |
| 2:20–2:42 | `05-settings-backup.png` | 展示加密备份与恢复密钥；说明工作数据库仍是受 OS ACL 保护的明文 SQLite，备份才使用 AES-256-GCM。 |
| 2:42–3:00 | 评测回执或终端截图 | 展示固定任务集、真实模型/规则对比、测试数量和证据 SHA-256；明确这是本地工程验收，不是外部有效性研究。 |

## 逐句口播

### 0:00–0:20

“Q-One 是一个本地优先、证据可审计的个人决策 Agent。普通 Agent 给你一段建议；Q-One 还会保留建议引用的候选、输入摘要、规则或模型来源，以及可以核对的内容哈希。”

### 0:20–0:45

“桌面界面和 Python 业务服务分离。服务只监听随机回环端口，Electron 每次启动生成一次性 capability。页面本身拿不到 capability，也不能直接访问 Node。”

### 0:45–1:20

“首次启动不要求账号，也不强制下载模型。用户只选择语言、写下第一个目标；备份位置和本地模型都可以跳过。没有模型时，规则路径仍然能生成行动、第一步和完成标准。”

### 1:20–1:55

“这里展示的是建议本身，不是成功概率。建议必须对应已有目标或任务，并给出本次可验收的产出。启用 Qwen3-0.6B 后，模型也只能引用现有候选 ID；格式不合格会回退规则建议。”

### 1:55–2:20

“采纳建议只会创建一个今天的任务，不会自动执行，也不会自动宣告目标完成。完成行动和提交复盘分别产生独立记录，后续推荐读取这些新证据。”

### 2:20–2:42

“备份使用随机数据密钥和 AES-256-GCM，恢复密钥通过 Argon2id 包装数据密钥。恢复先写入 staging 目录，验证后再原子切换；失败时保留原数据。需要说明，工作数据库不是端到端加密，它依赖操作系统 ACL。”

### 2:42–3:00

“这个项目最有价值的不是功能数量，而是证据链：真实 Electron E2E、固定哈希模型、可复算评测、未闭合 claim 不进入发布。它目前是可验证的本地工程成果，不是已正式发布的三平台商业产品。”

## 简历版收尾

“我做的核心工作，是把一个容易停留在 Demo 的 Agent，推进到具备本地运行边界、失败降级、加密恢复和可复算证据链的桌面系统。下一阶段是签名、三平台干净机器安装和真实用户测试。”
