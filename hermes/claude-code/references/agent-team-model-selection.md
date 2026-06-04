# Claude Code Agent Team — Worker 模型选择机制

> 研究日期：2026-06-01 · 来源：官方文档 + GitHub Issues + 社区项目

## 核心结论

**Claude Code agent team 不内置按任务自动选择 worker 模型的能力。** Teammate 用固定默认值，不继承 leader 的 `/model`，也不会根据任务复杂度自主匹配模型。

## 当前三种模型设置方式

| 方式 | 粒度 | 用法 |
|:---|:---|:---|
| **自然语言** | 单次 spawn | `"Use Sonnet for each teammate"` |
| **`teammateDefaultModel`** | 全局 | `settings.json`: `"sonnet"` / `"opus"` / `null`(跟 leader) |
| **Subagent 定义 `model`** | 按角色 | `.claude/agents/<name>.md` frontmatter |

### 官方文档原话

> "Teammates don't inherit the lead's `/model` selection by default. To change the model used when the prompt doesn't specify one, set Default teammate model in `/config`."

来源：[code.claude.com/docs/en/agent-teams](https://code.claude.com/docs/en/agent-teams#specify-teammates-and-models)

### 模型解析优先级

`CLAUDE_CODE_SUBAGENT_MODEL` env var > prompt 自然语言 > subagent 定义 `model` > `teammateDefaultModel` > 系统默认

## 社区方案

### claude-model-router-hook

[tzachbon/claude-model-router-hook](https://github.com/tzachbon/claude-model-router-hook) — 零 API 调用，关键词分类 prompt 复杂度，可选 `autoswitch`。

### PreToolUse Hook 按角色路由

来源：[Issue #32110](https://github.com/anthropics/claude-code/issues/32110)

```bash
case "$NAME" in
  researcher|explorer) MODEL="sonnet" ;;
  implementer|coder)   MODEL="opus" ;;
  reviewer|tester)     MODEL="haiku" ;;
esac
```

## 开源 Feature Requests

| Issue | 内容 | 状态 |
|:---|:---|:---|
| [#43326](https://github.com/anthropics/claude-code/issues/43326) | Auto-select model + effort based on task complexity | Open |
| [#39282](https://github.com/anthropics/claude-code/issues/39282) | `model: auto` setting, route by task type | Open |
| [#32110](https://github.com/anthropics/claude-code/issues/32110) | Per-teammate model config + PreToolUse hook workaround | Open |
| [#31430](https://github.com/anthropics/claude-code/issues/31430) | Per-agent model via `model` parameter (40-60% cost saving estimate) | Open |

## 对 claude-code skill 的建议

1. 补充 teammate 模型选择指南 — 智能 Effort 路由只覆盖 leader，未涉及 teammate
2. 评估 `claude-model-router-hook` 集成
3. 关注 #43326 — `model: auto` 落地后 Effort 路由可直接扩展为 Model 路由
4. 按角色预设映射：`security-reviewer → opus`, `test-writer → sonnet`, `formatter → haiku`
