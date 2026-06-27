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

| **Lesson:** When architectures differ fundamentally, the right move is usually a lightweight references file, not a SKILL.md restructure.

## Case Study: self-evolution + SkillClaw + oh-my-hermes → skill-authoring (2026-05-31)

| | Three external projects | skill-authoring v3.0 + governance ecosystem |
|:---|:---|:---|
| Architecture | Evolution engine / proxy infrastructure / multi-agent orchestration | Skill creation pipeline + compliance framework |
| Core problem | Optimize skill text / dedup skill library / orchestrate agents | Ensure agents FOLLOW created skills |
| Same problem? | ⚠️ Partial overlap — all about skill quality, but at different layers |

**Initial absorption plan (over-engineered):** 4 phases, 48-71 hours, new skill-hygiene skill, Step 3.5 dual-role review, Step 8 enhancement, Step 11 PR metrics, dashboard.

**CC 3-lens review found:** Circular compliance failure (modifying governance skill without re-governing itself), curator overlap unresolved, governance-incomplete new skill, line budget violation risk.

**Lean outcome (1.5-2 hours):**
- Wrote `references/dual-role-patterns.md` — two-pass cached review pattern (Advocate→Challenger→Synthesize), not embedded in SKILL.md body
- self-evolution kept as external tool, not absorbed into any workflow
- SkillClaw's dedup/merge capability deferred to simple scan script (when needed)
- No SKILL.md modifications, no new skills created

**Lesson:** When absorption crosses from "add a reference file" to "restructure the governance framework," STOP. Three small GitHub projects with partial architecture fit produced a 48-hour plan that collapsed to 1.5 hours once the CC review forced us to separate genuine gaps from interesting-but-not-actionable ideas. The reflexivity trap (modifying governance without re-governing) was the canary — if the absorption plan would fail its own compliance checklist, it's over-engineered.

## Case Study: SkillEvolver + EmbodiSkill → skill-authoring (2026-05-27)

| | SkillEvolver/EmbodiSkill | skill-authoring v2.0 |
|:---|:---|:---|
| Architecture | Skill evolution loop (deploy→observe→reflect→revise) | Skill creation pipeline (capture→grill→audit→score→deploy) |
| Core problem | Skills go stale after creation | Agents don't follow created skills |
| Same problem? | ✅ Both about skill quality — complementary, not conflicting |

**What we did:** Absorbed 4 key mechanisms (deployment-grounded audit, failure classification, targeted revision, silent-bypass detection) into the creation pipeline. Architecture was compatible — creation → deployment is a natural extension.

## Case Study: kepano/obsidian-skills → obsidian + obsidian-md-ac (2026-05-29)

| | kepano/obsidian-skills | obsidian + obsidian-md-ac |
|:---|:---|:---|
| Architecture | Agent Skills spec, 5 standalone skills | Hermes-native, 2 class-level skills with references/ |
| Core problem | "How to teach agents to use Obsidian" | Same — already solved, gaps in Bases/Canvas/CLI/plugin-dev |
| Same problem? | ✅ Same domain, different implementation style |

**Pattern: external Agent Skills spec repo → Hermes skill absorption**

1. **Survey**: L1 GitHub code-explorer (Exa fetch README + `gh api` directory listing)
2. **Map to existing**: identify gaps, overlaps, partial overlaps
3. **Integrate via progressive disclosure**: substantial content → `references/*.md`, thin pointers in SKILL.md
4. **Trim to <300 lines**: move verbose sections (e.g. Best Practices) to references if budget exceeded
5. **Add compliance**: Red Flags table + Verification Checklist per updated skill
6. **Score**: 7-dim compliance, all ≥4
7. **Deploy**: sync to profiles → sanitize → jz-skills → push

**What went in where:**

| External skill | Outcome | Reason |
|:---|:---|:---|
| obsidian-markdown | ❌ Skipped | Already more comprehensive in existing obsidian-syntax.md |
| obsidian-cli | `obsidian/references/obsidian-cli.md` | New capability (CLI + plugin dev) |
| obsidian-bases | `obsidian/references/obsidian-bases.md` | New capability (.base files) |
| json-canvas | `obsidian-md-ac/references/json-canvas.md` | New capability (.canvas files) |
| defuddle | Inline in obsidian SKILL.md | Small enough (~10 lines) |

**Line budget result:** obsidian 158→228, obsidian-md-ac 276→300 (trimmed Best Practices to pointer).

**Lesson:** Map by domain (vault ops vs content creation), use references/ for substantial content, score before shipping.

## Checklist: Before Absorbing

- [ ] Is the external solution solving the SAME class of problem as the target skill?
- [ ] Is the architecture compatible? (pipeline vs loop, single vs multi-engine, CLI vs MCP)
- [ ] If absorbing: does the change fit in <300 lines? Or does it need a new references/ file?
- [ ] If NOT absorbing: is there a lightweight alternative (references file, one-line pointer)?
- [ ] Did I ask: "would this actually help, or does it just look clever?"
