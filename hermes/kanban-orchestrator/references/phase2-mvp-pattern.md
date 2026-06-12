# Phase 2 MVP Pattern — From Smoke Testing to Value Production

## What Phase 2 means

Phase 0-1.1 proved the plumbing: Kanban handoff, CC lane visibility, intervention, disk verification, cross-substrate contract, adversarial review gate. Phase 2 is the transition from "does the pipe hold water" to "does the pipe deliver something the user actually wants."

The key test: can Kanban + CC lane produce a real artifact on a real vault task, with adversarial review catching real (not staged) issues?

## Card structure

Always a **two-card pair**:

### Card A — Implementation (default)

```python
kanban_create(
    title="Phase 2: <real task name> (implementation)",
    assignee="default",
    skills=["claude-code", "kanban-orchestrator", "<domain-skill>"],
    max_runtime="45m",  # real tasks need more time than smoke
    body="""
### Task
<specific, scoped, real task — not a smoke dummy>

### Allowed
- Read <specific vault paths>
- Write ONLY to <isolated /tmp/ path>

### Forbidden (explicit list)
- NO writes to Obsidian vault
- NO ~/.hermes/skills/, config.yaml, gateway, cron, Surge, secrets

### Substrate
metadata.cc_lane.substrate = "claude-code/tmux"  # mature substrate for first real task

### Monitoring (红线①)
Every capture-pane → 📡 CC Agent Team block

### Verification
ls -la <output path> && wc -l <output path>

### Final Input-Line Gate
capture-pane -S -3 | tail -1 — check ❯ before kill-session
""",
)
```

### Card B — Review (regent, adversarial)

```python
import time

kanban_create(
    title="Phase 2: <real task name> (review)",
    assignee="regent",
    parents=[implementation_task_id],
    skills=["claude-code", "kanban-orchestrator"],
    max_runtime="25m",
    body="""
Adversarial review of Card A.

### Adversarial Prompt (D17 Gap 2 — mandatory)
metadata.review.adversarial_prompt: "<task-specific counterfactual question>"

### Review Checklist
See cc-lane-dual-substrate-template.md review child checklist.

### Decision
pass | request changes | reject
""",
    metadata={
        "review": {
            "adversarial_prompt": (
                "Before approving, list 3 specific ways this <artifact> could "
                "be wrong or incomplete, then explain why each is inapplicable or mitigated."
            ),
        },
        "parent_timeout_at": int(time.time()) + 3600,
    },
)
```

## Substrate selection for real tasks

| Task type | Substrate | Reason |
|:---|:---|:---|
| First real task | `claude-code/tmux` | Mature, proven, lower variable count |
| Subsequent real tasks | Either | `cccmux/cmux` if visibility/intervention is critical; `claude-code/tmux` otherwise |
| Critical config/security | `claude-code/tmux` + heterogeneous gate | Need mature substrate + MoA/external-model review |

## Acceptance criteria for "value" vs "plumbing"

Phase 2 task is a **value pass** when:
1. The artifact is **usable as-is** by the user (not "would be usable after cleanup")
2. Adversarial review found **at least one real issue** (however minor) — proves the gate catches things, not just rubber-stamps
3. The review issues are **actionable** — each has a specific fix, not vague "consider rethinking"
4. The user could, if they chose, act on the artifact immediately

## Anti-patterns (what NOT to call Phase 2)

- Another smoke test with a different substrate ("Phase 2: cmux smoke" — that's still Phase 1.1)
- A task so trivial that adversarial review can't possibly find anything ("add one line to README")
- A task that touches the same skill/docs as the smoke tests (circular — testing the tester)

## Evidence: D19 Phase 2 MVP (2026-06-12)

Task: Inbox classification scan — 22 real vault notes, classify + frontmatter audit + target zone suggestion.

| Metric | Value |
|:---|:---|
| Substrate | `claude-code/tmux` |
| CC model | Opus 4.8 · effort high |
| 📡 blocks | 5 during execution |
| Artifact | report.md · 336 lines · 19.5KB |
| Adversarial prompt | 3 counterfactuals answered |
| Review result | PASS · 8/8 checklist |
| Real issues found | 2 (type enum standardization, tag alignment) |
| User-actionable | Yes — report can directly guide Inbox triage |

This task passed the value criteria: the artifact was immediately usable, adversarial review found real (minor) issues, both were actionable, and the user could act on the report without further processing.
