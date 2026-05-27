# 将作监 v1.0 — Full 三省六部 Workflow Example

> Reference for: how a complete 三省六部 lifecycle looks when it works correctly.

## Task: Formalize the 将作监 (External Engineering Bureau) integration spec

### Task Graph

```
T1(t_a5410cc2) → planner  拟制将作监 v1.0 接入规范
  ├── T2(t_9bf996ba) → reviewer  审查规范
  ├── T3(t_b32d78af) → engineer  Claude Code 连通性验证
  └── T4(t_06605d5e) → archivist 归档规范
```

T2, T3, T4 all depend on T1 (parent link). Once T1 completes, all three promote to `ready` and run in parallel.

### Input Materials (provided in T1 body)

1. claude-code skill (full SKILL.md — 500+ lines of CLI reference)
2. alex-longterm-agent-team-preference (user preferences)
3. Existing external-expert-spec.md (v0.1 draft to upgrade)
4. Claude Octopus MCP config (5 tools, regent profile)
5. User rules: default to agent team; print mode only for one-shot

### Results

| Task | Role | Duration | Output |
|------|------|----------|--------|
| T1 | planner (kimi-k2.6) | 387s | 将作监-v1.0-接入规范.md (535 lines, 17KB) |
| T2 | reviewer (deepseek-v4-pro) | ~38s | Verdict: approve + 2 non-blocking suggestions |
| T3 | engineer | running | Claude Code smoke test in progress |
| T4 | archivist | running | Archiving in progress |

### T1 Output Highlights

- **4 call modes**: tmux interactive (default), print mode `-p`, MCP Bridge, Codex (backup)
- **Decision flowchart**: when to use which mode
- **Task brief template**: YAML schema with 9 required fields
- **Output requirements**: changed_files + diff_summary + test_log + risk_note + session metadata
- **Audit checklist**: 5 dimensions × 5 items for 御史台
- **Health check script**: `check-claude-code-env.sh` — verifies Claude Code, auth, tmux, MCP, Codex
- **15 common pitfalls** with countermeasures
- **Environment snapshot**: Claude Code ✅, tmux ✅, MCP ✅, Codex ❌

### Errors Caught

1. **Planner claimed Claude Code was unauthenticated** — user corrected; actually authenticated. Reviewer missed this.
2. **Reviewer did not catch the auth error** — passed through to orchestrator. Orchestrator must spot-check.

### Lessons

1. **三省六部 works for research/synthesis tasks** — planner + reviewer + engineer + archivist is the right chain even for "just write a spec" tasks
2. **Reviewers miss errors** — orchestrator spot-check of factual claims is essential
3. **Long bodies work** — passing full context in `kanban_create --body` with `shlex.quote()` is reliable
4. **Parallel dispatch after T1** — reviewer, engineer, archivist all ran simultaneously once planner finished
