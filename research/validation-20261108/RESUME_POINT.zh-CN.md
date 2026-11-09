# 云端算力续跑点（2026-11-08 暂停）

## 暂停原因

用户指示：云端算力线暂缓，等 AMD 主机空闲后再继续。当前主机 GPU 使用率 96%，
VRAM 已用 28849803264 / 51522830336 字节，属于其他会话/用户的作业，
不终止、不抢占。

## 恢复条件（满足任一即恢复）

1. `rocm-smi` 显示 GPU use 低于 20%，且 VRAM 空闲不少于 20 GB。
2. 用户明确说继续。

检查命令：

```bash
ssh -p 36095 root@36.150.116.206 \
  "/opt/rocm/bin/rocm-smi --showmeminfo vram --showuse"
```

## 恢复后的第一件事

在 `/root/qone-paperbench-full10/` 下跑一个隔离的短任务（不写共享输出目录），
优先顺序：

1. `mechanistic-understanding` 的 DPO / PPLM / SVD 扩叶子（已有 GPT-2-medium、
   Jigsaw、RealToxicityPrompts 资产）。
2. `fre` / `rice` 的最小离线 RL baseline（D4RL Kitchen 已下载，先 BC/MLP）。
3. 其余任务仍受 gated_data / long_rl / 权重缺口限制，不伪造推进。

## 未决决策（不属于算力线）

用上游 `SimpleJudge` 无法凑齐锁定三模型面板：DeepSeek Free 工具注入不可用，
Flint/Xing4 在同一叶子上 spread=1.0。选项：接受两模型（永久 BLOCKED）、
按通道兼容性替换一个模型、或维持现状。此决策未定前不跑批量 judge。

## 当前证据状态

- 主验证闸 216 项 PASS；continuation 67 项 PASS；审计闸 18 项 PASS。
- Full10 `BLOCKED`，`problems=0`；3 verified / 22 waived / 2751 blocked。
- 免费通道单叶子冒烟 PASS（非官方、不晋级）。
