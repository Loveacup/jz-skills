# Agent Team Skill/Workflow Audit Recipe

Proven pattern (validated 2026-05-27): use Claude Code agent team to audit skills, workflows,
configs, or any structured document. Produces P0/P1/P2 prioritized findings with concrete fixes.

## When to Use

- Auditing a Hermes skill for anti-patterns, security holes, or drift
- Reviewing a workflow definition (Kanban chains, cron jobs, MCP configs)
- Stress-testing a design doc or architecture decision against real constraints
- Any structured artifact where 3+ independent lenses produce richer signal than one

## Recipe

### Step 1: Prepare Context

Bundle the artifact(s) into a single prompt payload:
- The skill/workflow file itself (paste inline or reference by path CC can read)
- Any relevant audit criteria (review report, compliance checklist, prior incidents)

### Step 2: Send to CC Agent Team (via tmux or print mode)

```
Review this skill file for anti-patterns, security issues, and structural problems.
Spawn 3 parallel agents with different lenses:

1. Security lens: secrets leakage, path injection, unsafe defaults
2. Architecture lens: hardcoded paths, missing fallbacks, single-points-of-failure
3. Operations lens: deployment hazards, persistence hygiene, error handling gaps

Requirements:
- Produce P0 (fix immediately), P1 (fix soon), P2 (optimize) prioritized findings
- Each finding must include the exact line/pattern that's wrong AND the fix
- Merge all findings into one report at /tmp/cc-agent-team-review.md
- The merged report must be Telegram-readable bullet markdown (no pipe tables)
- Report how many agents were spawned and which workflow was used
```

### Step 3: Read the Report

```bash
cat /tmp/cc-agent-team-review.md
```

### Step 4: Apply Fixes

Use the P0/P1/P2 findings to patch the target artifact. Each finding already contains
the old_string and new_string — apply them directly with the `patch` tool.

### Step 5: Verify

- Re-load the patched skill with `skill_view()` to confirm no ambiguity
- Run any smoke tests defined in the skill's verification checklist
- Delete `/tmp/cc-agent-team-review.md` if sensitive

## Proven Results

First run (morning-news-briefing v3.0 audit):
- 3 agents (security/architecture/operations), all completed
- 124-line report, 7.8KB
- 6 findings: 2×P0, 1×P1, 2×P2, 1×duplicate detected
- All 6 addressed in 8 patches across 2 files

## Pitfalls

- The merged report path in the prompt must match what you `cat` afterwards
- If the artifact references other files (references/, assets/), mention them in context
  so agents can trace dependencies
- Telegram pipe tables get mangled — explicitly ask for bullet markdown
- Don't ask agents to apply fixes themselves — they may not have write access to the skill dir
