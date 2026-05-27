# Agent Pipeline (Full — Claude Code Pseudo-Code)

> This is the detailed Claude Code TeamCreate/TaskCreate pipeline. In Hermes, use `delegate_task` with manual orchestration.

## 16-Agent Dispatch Flow

```
Stage -1 (D/S): question-refiner → intent assessment + structured prompt
Stage 0  (D/S): memory_reader.py → memory-context.json
Stage 0  (ALL): topic-preprocessor → topic analysis + material summary
Stage 0.5(ALL): knowledge-enricher → qmd + Exa + history
Stage 1  (ALL): framework-builder → S-T-D + multi-dimensional frameworks
Stage 1.5(D):   got-controller → dimension scoring + resource allocation
Stage 2  (ALL): spatial-researcher ∥ temporal-researcher ∥ domain-researcher
         (D/S): + stakeholder-analyst ∥ causal-analyst
Stage 3  (D):   source-manager → CoV 3-layer verification
Stage 4  (ALL): insight-synthesizer → multi-order inference + cross-matrix
Stage 5  (ALL): longform-writer → single file + CoT embedded + source index
Stage 6  (D/S): output-finalizer → audit + naming + revision loop
Stage 6.5(ALL): Leader calls obsidian-md-ac for formatting
Stage 7  (D):   memory-curator ∥ pattern-crystallizer
```

## Hermes Mapping

| Claude Code | Hermes |
|-------------|--------|
| `TeamCreate(...)` | Create temp workspace directory |
| `TaskCreate(...)` + `Task(...)` | `delegate_task(goal=..., context=...)` |
| `SendMessage(...)` | `clarify(question=..., choices=[...])` |
| `Skill("obsidian-md-ac")` | Manual Obsidian formatting by main agent |
| `TeamDelete()` | Cleanup workspace |
| `run_script(...)` | `terminal(command="python ...")` |

## Agent Task Definitions (for reference)

See `references/agent-roster.md` for the full 16-agent table with descriptions, modes, and stage assignments.
