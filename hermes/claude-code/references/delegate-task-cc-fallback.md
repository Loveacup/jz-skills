# delegate_task 作为 CC 兜底方案

> ⚠️ **严禁主动选用。** 当用户说"拉 CC / 调用 skill / agent team"时，delegate_task 不是备选——必须先试 CC。本方案仅限 CC 反复卡死（连续 3+ 次 thinking loop、token 冻结 >3min、`Ctrl+C`+单行命令 ≥2 次仍无效）时的最后兜底。**用 delegate_task 替代 CC agent team = 违规。** 2026-06-08 用户明确纠正："不行啊，一定要调用cc agent team。你别自己来。"

## 适用场景（全部满足才触发）

- CC xhigh effort 持续 Mulling/Bootstrapping/Crafting >3min 且 token 完全冻结，无法 spawn worker
- 已尝试 `Ctrl+C` + 单行推动命令 >= **3 次**，仍然不生效
- 已尝试 `mkdir /tmp/cc-fresh-*` 全新空目录重建 session 至少 1 次
- 任务可以拆分为 2-4 个独立子任务（如多 Lens 分析）
- 用户要求必须产出、或已等 CC 超过 15min 无进展

## 不适用场景（走 CC）

- 用户说"拉 CC / 调用 skill / agent team" → **必须先试 CC**，不能直接选 delegate_task
- CC 正在活跃调用工具（`●`）/ worker token 在增长 → 继续等
- CC 已成功 spawn worker 但运行慢 → 继续等，用 📡 汇报
- 单文件小修 → Hermes 自己做

## 使用模式

```python
# 模式 1：3 Lens 并行分析（内容研究/对比分析类任务）
delegate_task(tasks=[
    {"goal": "Lens 1 分析写入 /tmp/lens1.md", "context": "完整事实+要求（必须自包含，subagent 无本轮记忆）...", "toolsets": ["terminal","file","web"]},
    {"goal": "Lens 2 分析写入 /tmp/lens2.md", "context": "完整事实+要求...", "toolsets": ["terminal","file","web"]},
    {"goal": "Lens 3 分析写入 /tmp/lens3.md", "context": "完整事实+要求...", "toolsets": ["terminal","file","web"]},
])

# 模式 2：4 并行（3 Lens + 综合行动建议）
delegate_task(tasks=[
    {"goal": "Lens 1 写入...", ...},
    {"goal": "Lens 2 写入...", ...},
    {"goal": "Lens 3 写入...", ...},
    {"goal": "综合 P0/P1/P2 写入 /tmp/actions.md", ...},
])
```

## 碎片验证与合并

```bash
# 验证所有碎片落地
ls -la /tmp/lens1.md /tmp/lens2.md /tmp/lens3.md
# Hermes 自己 cat 合并 + 添加 YAML frontmatter
cat /tmp/_head.md /tmp/lens1.md /tmp/lens2.md /tmp/lens3.md /tmp/_tail.md > 最终输出路径
```

## 实战记录

- 2026-06-08：CC v2 session **连续 3 次**卡在 Mulling/Bootstrapping 思考循环 3-6min 无法 spawn worker。用户说"不行啊，一定要调用cc agent team"后，Hermes 先试了新 CC session（v3），v3 成功 spawn。后续 v4 也成功。关键教训：**不能因为一次 CC 卡死就永久退到 delegate_task，要先试干净 session。**
- 2026-06-08（另一轮）：CC 也被卡住时，delegate_task 3 并行 subagent → 各自 ~140s 产出 300-470 行分析 → Hermes 验证碎片落地 → 合并输出。
