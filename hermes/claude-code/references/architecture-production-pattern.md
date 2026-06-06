# Architecture Document Production via CC Agent Team

> Pattern discovered 2026-06-05 during "skill 计数自动结晶" research-to-architecture pipeline.
> Applies when CC agent team needs to produce design/architecture documents from research findings.

## The Problem

First-round agent team produced minimal output:
- Agent 1 (计量): 52 tools, 43.7k tokens — did deep exploration of actual infrastructure
- Agents 2-4 (审计/检索/结晶): 2 tools each, 11.3k tokens — only read 2 files and returned
- Result: exploration-heavy, design-light

## The Fix

Two corrections to the leader:

1. **不过度勘探 (No excessive exploration)**: Inline the spec directly into agent prompts. Agents should NOT read context files, explore codebases, or probe infrastructure — they already have everything they need.
2. **Agent 直接 Output (Agents write directly)**: Each agent writes its section to a separate file. Leader does NOT summarize or rewrite — only mechanical `cat` concatenation.

### Corrected prompt to CC leader:
```
agent team 直接写架构文档，不用过度勘探。每个 agent 写完后直接 Output，不要等 leader 汇总。
```

### What the leader should do:
1. Pin a shared data contract (field names, paths, schemas) — distributed to all agents
2. Inline the module spec into each agent's prompt (no file reads needed)
3. Each agent writes to `cc-arch-module-{N}-{name}.md`
4. Leader `cat`s the files together — no rewriting

## When To Use

- Architecture/design documents where the spec is already well-defined
- Multi-module documents that can be cleanly split by concern
- When the first agent team round produces exploration-heavy, design-light output

## When NOT To Use

- Root-cause debugging (needs exploration)
- Research tasks (needs discovery)
- Single-file changes
- Tasks where agents genuinely need to read context files
