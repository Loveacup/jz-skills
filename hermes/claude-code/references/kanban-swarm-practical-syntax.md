# Kanban Swarm: 实测 CLI vs 概念语法

> **触发条件：** 设计 Kanban Swarm 集成、写 swarm 命令、或调试 `hermes kanban swarm` 失败时，参考此文件。不要相信记忆中的语法——概念 docs 和实测 CLI 有显著差异。

## 发现背景

2026-06-03 早新闻 v4.0 设计。SKILL.md 写了概念语法：
```bash
hermes kanban swarm --goal "..." --workers 4 --verifier --synthesizer \
  --worker-model deepseek-v4-pro --verifier-model claude-sonnet-4
```

CC agent team 审查时对照实测 CLI 发现 4 个 flag 不存在。

## 实测 CLI (v0.15)

```bash
hermes kanban swarm \
  --goal "目标描述" \
  --worker PROFILE:TITLE[:SKILL,SKILL] \    # 可重复，每个并行 worker 一个
  --verifier VERIFIER_PROFILE \             # 验证节点 profile 名
  --synthesizer SYNTHESIZER_PROFILE         # 合成/交付 profile 名
  [--tenant TENANT] \                       # 可选：租户命名空间
  [--priority PRIORITY] \                   # 可选：优先级
  [--json]                                   # 可选：JSON 输出
```

## 关键纠正

| 概念假设 | 实测真相 |
|----------|---------|
| `--workers N`（数量 flag） | ❌ 不存在。每个并行 worker 用独立的 `--worker PROFILE:TITLE` |
| `--worker-profile` / `--worker-title` | ❌ 这两个 flag 不存在。格式是单 flag `--worker PROFILE:TITLE[:SKILL,SKILL]` |
| `--worker-model deepseek-v4-pro` | ❌ 没有 per-flag model override。Model 由**各 profile 的 `config.yaml`** 控制 |
| `--verifier-model claude-sonnet-4` | ❌ 同上。verifier model 在 verifier profile 的 config.yaml 里 |
| Hermes 有原生 kanban SKILL.md | ❌ Kanban 是 **plugin**（`plugins/kanban/`），不是 skill。Agent 通过 `kanban_*` 工具族操作 |

## Worker 格式详解

```
--worker PROFILE:TITLE[:SKILL,SKILL]
```

- `PROFILE`：已存在的 Hermes profile 名（如 `lane-zh`、`engineer`）
- `TITLE`：此 worker 的任务标题（自由文本）
- `SKILL,SKILL`：可选，启动时预加载的 skill 名列表

示例：
```bash
--worker lane-zh:搜索中文新闻:web-research-router
--worker auditor:验证内容质量:source-verification
```

## Model override 的正确做法

不同 worker 用不同模型 → 在各 profile 的 `config.yaml` 中分别设置 `model`：

```yaml
# ~/.hermes/profiles/lane-zh/config.yaml
model: deepseek-v4-pro          # 便宜，搜索任务

# ~/.hermes/profiles/auditor/config.yaml  
model: claude-sonnet-4          # 高质量，审查任务
```

## 教训

**涉及 Hermes 内置功能（Kanban、profiles、gateway）的集成设计，先跑 `hermes <command> --help` 核实 CLI 语法，不要基于文档/博客/研究笔记的概念示例直接写命令。** CLI 输出是单一真实来源。
