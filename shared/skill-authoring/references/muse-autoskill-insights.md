# MUSE-Autoskill: Skill Lifecycle Design Patterns for Hermes

> Source: "MUSE-Autoskill: Self-Evolving Agents via Skill Creation, Memory, Management, and Evaluation" (ByteDance + RIT, arxiv 2605.27366, 2026-05-26)
> Analysis date: 2026-06-04

## Key Concepts

MUSE-Autoskill proposes a 5-stage skill lifecycle:
1. **Creation** — agent discovers gap during task → writes spec → framework generates skill package
2. **Memory** — per-skill `.memory.md` accumulates failure modes, format quirks, performance notes
3. **Management** — merge overlapping skills, prune unused, update failing ones
4. **Evaluation** — sandbox runs tests/ → pass before registering in skill bank
5. **Refinement** — test failure or runtime error → agent reads error trace → `update_skill` → retest

## Skill Package Structure (Anthropic-compatible)

```
skill-name/
├── SKILL.md          # YAML frontmatter + body
├── .memory.md        # per-skill accumulated experience
├── scripts/          # executable code
├── tests/            # pytest-compatible tests
├── resources/        # data / docs
└── references/       # reference materials
```

Hermes already supports `SKILL.md + references/ + scripts/ + templates/ + assets/`. Missing: `.memory.md` and `tests/`.

## Three Actionable Takeaways for Hermes

### 1. Per-skill `.memory.md` (low effort, high impact)

Each skill gets a `.memory.md` file alongside `SKILL.md`. Agent appends after each use:
- Failure modes encountered
- Input format edge cases
- Performance quirks
- Calling experience

Next time the agent loads the skill, `.memory.md` is injected together.

**Implementation**: Add to skill-authoring's create flow. Existing skills can start with empty `.memory.md`.

### 2. Test gating for skill creation

Before registering a new skill, run basic smoke tests:
- Does SKILL.md YAML parse?
- Do referenced files exist?
- Can the skill be loaded via `skill_view`?

**Implementation**: Add a `tests/` directory generation step to skill-authoring's create flow. Simple checks that catch the most common mistakes (P0: YAML parse, file existence; P1: trigger test).

### 3. Skill bank health audit

Periodic check:
- Merge: skills with >70% description overlap
- Prune: skills unused for >90 days
- Repair: skills with failed test coverage

**Implementation**: Lightweight cron job or manual command that reports health, doesn't auto-modify.

## What NOT to Absorb (Yet)

- **Runtime autonomous skill creation**: MUSE lets the agent decide when to create skills during task execution. This is a different paradigm from Hermes' human-driven skill creation. Quality risks without sandbox isolation.
- **Sandbox execution**: Hermes runs on user machines without isolated execution environments. MUSE's test sandbox model doesn't directly translate.

## Experiment Data (for reference)

- SkillsBench: 51 real tasks, 4 super-domains, GPT-5.5 backbone
- Human skills: 53.19% → 68.40% (+15.21%)
- Auto-generated (35/51 tasks): 87.94% on successful generations
- Cross-agent transfer: MUSE skills → Hermes: 47.89% → 58.40% (closes 79% of gap)
- Break-even: ~3 reuses amortize generation cost (383K tokens)
- Key bottleneck: 16/51 tasks couldn't generate skills (no successful first-stage trajectory to distill from)
- Critical risk: single-trajectory distillation can solidify accidental success conditions (HBC control case: 80% → 20% when noise distribution changed)

## Related

- Obsidian note: `02-Plan&CQI/Hermes Kanban 五种工作模式_20260604.md` and `00-Inbox/B站笔记_MUSE-Autoskill_Skill生命周期_20260604.md`
- Paper: https://arxiv.org/abs/2605.27366
