# Regent 3S6M Multi-Agent Governance Pattern

Use this reference when a user wants a controlled multi-agent collaboration system with a main orchestrator, specialist agents, optional A2A communication, and subagent delegation.

## Core shape

```text
User / Telegram / CLI
  ↓
Regent main orchestrator
  ↓
Governance layer: planning → review gate → dispatch
  ↓
Kanban state layer: task graph, parent dependencies, claim, logs, done/blocked
  ↓
Expert execution layer: Hermes profiles, skills, external coding agents, MCP tools
  ↓
Audit + archive layer: verification, Obsidian, qmd indexing
```

Chinese institutional metaphor used in the originating design:

- 监国太子 / Regent: user-facing main agent and final coordinator.
- 中书省 / Planning Bureau: decomposes goals into structured task graphs; does not execute.
- 门下省 / Review Gate: reviews and can reject plans before execution.
- 尚书省 / Dispatch Bureau: creates Kanban tasks, binds dependencies, tracks state.
- 六部 / Ministries: capability domains and specialist pools, not a flat expert list.
- 御史台 / Audit Office: independently verifies results; does not execute.
- 史馆 / Archive Office: records durable conclusions into Obsidian/qmd; does not invent facts.
- 将作监 / External Engineering Experts: Claude Code/Codex/OpenCode as outside specialists, especially for multi-file coding tasks.

## Implementation stages

1. **Lightweight governance**: prompts/skills/workflows require structured task briefs and the planning → review → dispatch → audit → archive sequence.
2. **Kanban + profiles**: represent the task graph in Kanban. Use Hermes profiles for planner, reviewer, engineer/executor, auditor, archivist, etc.
3. **External expert pool**: wrap Claude Code/Codex/OpenCode as external expert agents. Require changed files, diff summary, test logs, and risk notes before audit.
4. **A2A adapter**: only after the Kanban/profile workflow is stable. Add Agent Cards and structured messages for controlled agent-to-agent communication.
5. **Subagent delegation**: allow expert agents to spawn temporary subagents with a bounded depth, usually `main → expert → subagent` only.

## Policy defaults

- Start with a **star topology**: main orchestrator coordinates specialists. Do not begin with free-form mesh communication.
- A2A is the communication layer; Kanban is the state/dependency layer; MCP is the tool layer.
- Horizontal expert-to-expert A2A requires `task_id`, permission, timeout, budget, and audit logging.
- Do not share one growing context across all agents. Pass context via structured briefs and references.
- Do not use prose like “wait for task X” as a dependency. Bind dependencies at task creation with `--parent` / `parents=[...]`.
- Do not allow recursive subagent trees. Default maximum depth: two delegation layers.

## Structured message / task brief fields

```yaml
task_id:
from:
to:
type: request | handoff | review | complete | block
objective:
scope:
inputs:
context_refs:
constraints:
acceptance_criteria:
timeout:
budget:
allowed_tools:
required_output:
```

## Knowledge-base sync pattern

When the architecture is updated in Obsidian, also ensure Obsidian is running for sync and refresh qmd for searchability:

```bash
pgrep -x Obsidian >/dev/null || open -a Obsidian --args --vault '<vault-path>'
qmd update -c <collection>
qmd embed -c <collection>
```

Capture durable architecture changes in the note/skill; do not store transient task IDs, run logs, or one-off progress in long-term memory.

## Profile model configuration (v0.4, 2026-05-18)

After a full-market research round comparing DeepSeek V4, Kimi K2.6, MiniMax M1, and GPT-5.4 across benchmarks (SWE-bench, LiveCodeBench, AA Intelligence Index, GDPval-AA), the following optimized config balances capability, speed, and simplicity:

| Profile | 角色 | 模型 | Provider | 选型理由 |
|---------|------|------|----------|----------|
| regent | 监国太子 | deepseek-v4-pro | deepseek | agentic coding 最强, SWE-bench 80.6%, 1M ctx |
| planner | 中书省 | kimi-k2.6 | moonshot | AA#4 全球, 134t/s 最快, 强推理规划 |
| reviewer | 门下省 | deepseek-v4-pro | deepseek | 审查需最高可靠性, agent 能力顶尖 |
| engineer | 工部 | deepseek-v4-flash | deepseek | SWE-bench 79.0%, 仅比 Pro 低 1.6%, 极便宜 |
| auditor | 御史台 | deepseek-v4-pro | deepseek | 1M 上下文可全文审计, GDPval-AA 1554 |
| archivist | 史馆 | deepseek-v4-flash | deepseek | 轻量文件/索引任务, 最便宜 |

**Design principle**: 2 providers (deepseek + moonshot), 3 model tiers (kimi-k2.6, v4-pro, v4-flash). No unnecessary provider diversity.

**Key benchmarks referenced**:
- DeepSeek V4-Pro: 1.6T/49B MoE, 1M ctx, SWE-bench 80.6%, hallucination 94% (answers when unsure)
- DeepSeek V4-Flash: 284B/13B MoE, 1M ctx, SWE-bench 79.0%
- Kimi K2.6: 1T/32B MoE, 262K ctx, SWE-bench 80.2%, AA#4 global, 134 t/s
- Source: deepseekai.guide, artificialanalysis.ai, tokencost.app (all April-May 2026)

See `references/model-config-optimization.md` for the full research-to-deployment workflow.

## Profile tuning (v0.4.x, 2026-05-18)

After实战验证, two profile-level fixes applied:

### Engineer: no self-block
**Problem**: engineer profile would `kanban_block` itself with reason "review-required" after completing work, because its system_prompt implicitly assumed external review was needed before merging.
**Fix**: engineer system_prompt now includes: "**自测通过即 kanban_complete，不主动 block 等待审查——审查由 Kanban 下游 reviewer 任务负责。**"
**Lesson**: execution agents must treat their own task boundary as "self-tested and complete." Review is a separate downstream Kanban task, not a self-imposed gate.

### Archivist: max-runtime 120s → 180s
**Problem**: archivist tasks involving full qmd index refresh (700+ docs) routinely exceed 120s and timeout on first attempt.
**Fix**: `kanban.max_runtime: 180` in archivist profile config.
**Lesson**: archive tasks that touch qmd embedding need headroom above the default max-runtime.
