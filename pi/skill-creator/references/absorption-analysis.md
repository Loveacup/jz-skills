# Absorption Analysis · 吸收分析

When evaluating whether to absorb external capability (another skill, paper, tool) into an existing skill, run this checklist before making changes.

## Decision Framework

```
External inspiration found?
├── Same architecture? → Absorb if gap is real
│   Example: SkillEvolver has deployment-grounded audit, we had self-review → absorb
├── Different architecture? → STOP. Evaluate separately:
│   ├── Is the external problem our problem too?
│   │   YES → Extract the PRINCIPLE, not the implementation
│   │   NO  → Don't absorb. Different architectures solve different problems.
│   └── Example: AnySearch has runtime.conf caching for CLI startup overhead.
│       Our problem is cognitive overhead (decision tree), not I/O overhead.
│       Same word ("caching"), totally different problem → don't absorb.
└── Unsure? → Grill: write down what problem the external solves, what problem
    the target skill solves, and check if they match at the ARCHITECTURE level.
```

## Case Study: AnySearch → web-research-router (2026-05-27)

| | AnySearch | Web Research Router |
|:---|:---|:---|
| Architecture | Single-engine, unified API | Multi-engine, MCP tool routing |
| Core problem | CLI startup overhead (detect Python/Node/PowerShell every time) | Cognitive overhead (pick the right engine for the query type) |
| Key innovation | `runtime.conf` — cache platform detection result | 5-mode decision tree + local knowledge tier |
| Same problem? | ❌ Architecture mismatch |

**What we did:** Created one references file (`vertical-domains.md`) for the domain → engine mapping (the only genuinely transferable insight). Did not modify the decision tree, add batch search mode, or implement engine preference caching.

**Lesson:** When architectures differ fundamentally, the right move is usually a lightweight references file, not a SKILL.md restructure.

## Case Study: SkillEvolver + EmbodiSkill → skill-authoring (2026-05-27)

| | SkillEvolver/EmbodiSkill | skill-authoring v2.0 |
|:---|:---|:---|
| Architecture | Skill evolution loop (deploy→observe→reflect→revise) | Skill creation pipeline (capture→grill→audit→score→deploy) |
| Core problem | Skills go stale after creation | Agents don't follow created skills |
| Same problem? | ✅ Both about skill quality — complementary, not conflicting |

**What we did:** Absorbed 4 key mechanisms (deployment-grounded audit, failure classification, targeted revision, silent-bypass detection) into the creation pipeline. Architecture was compatible — creation → deployment is a natural extension.

## Checklist: Before Absorbing

- [ ] Is the external solution solving the SAME class of problem as the target skill?
- [ ] Is the architecture compatible? (pipeline vs loop, single vs multi-engine, CLI vs MCP)
- [ ] If absorbing: does the change fit in <300 lines? Or does it need a new references/ file?
- [ ] If NOT absorbing: is there a lightweight alternative (references file, one-line pointer)?
- [ ] Did I ask: "would this actually help, or does it just look clever?"
