# Agent-Direct-Output Pattern

## When to Use

CC agent team tasks where the output is multiple independent artifacts (architecture docs, review reports, code modules). Use this pattern instead of the default "leader synthesizes everything."

## Why

- Leader synthesis adds latency (leader must read all agent outputs, process, rewrite)
- At max effort, leader synthesis triggers thinking loops (>3min "almost done thinking" with frozen tokens)
- Agent-direct-output cuts latency by having each agent Write its own file, then leader only does mechanical merge

## Pattern

1. **Each agent writes its own file**: agent task prompt includes "Write output to /tmp/cc-<name>-<section>.md. Do not return to leader."
2. **Leader only cats**: after all agents finish, leader runs `cat /tmp/cc-*.md > /tmp/cc-final.md` — no reading, no rewriting
3. **Hermes validates**: Hermes checks file sizes on disk, not leader's self-report

## Agent Prompt Template

```
Write architecture document for module X.
Cover: responsibilities, data flow, data structures, implementation, dependencies, testing.
Write directly to /tmp/cc-arch-module-X.md. Do NOT return to leader.
```

## Constraints

- Only works when artifacts are truly independent (no shared state between agents)
- Shared data contract (field names, paths, schemas) must be pre-specified in the agent prompts
- Semantic cross-module consistency is NOT guaranteed — needs a separate reconciliation pass

## Proven Usage

2026-06-05: 4-module architecture draft for Hermes skill auto-crystallization.
- 4 agents wrote to /tmp/cc-arch-module-{1,2,3,4}.md
- Leader cat'd them into /tmp/cc-architecture-draft.md
- Total: 82KB in ~5min (vs. 8+ min leader synthesis with thinking loops)
- Caveat: 8 semantic interface issues found in subsequent reconciliation pass
