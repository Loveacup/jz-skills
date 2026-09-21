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

**Pattern: external skill or project → existing skill**

1. **Survey the real artifact and provenance** — use the appropriate repository/research route and record the reviewed revision.
2. **Map to the existing owner** — identify genuine gaps, overlaps, and architecture mismatches before proposing changes.
3. **Integrate by attention need** — keep common-path behavior in `SKILL.md`; move conditional depth to a named reference with a load condition.
4. **Preserve the behavior contract** — remove repetition and unrelated ceremony rather than optimizing for a fixed line ceiling.
5. **Add safeguards only for demonstrated risk** — do not require a warning table or checklist shape by default.
6. **Verify by change risk** — use scenarios selected from the changed behavior; high-impact changes need a fresh independent verdict.
7. **Prepare release state explicitly** — source/canonical update, runtime deployment, and publication are separate; execute only the named actions already authorized.

**What went in where:**

| External skill | Outcome | Reason |
|:---|:---|:---|
| obsidian-markdown | ❌ Skipped | Already more comprehensive in existing obsidian-syntax.md |
| obsidian-cli | `obsidian/references/obsidian-cli.md` | New capability (CLI + plugin dev) |
| obsidian-bases | `obsidian/references/obsidian-bases.md` | New capability (.base files) |
| json-canvas | `obsidian-md-ac/references/json-canvas.md` | New capability (.canvas files) |
| defuddle | Inline in obsidian SKILL.md | Small enough (~10 lines) |

**Line budget result:** obsidian 158→228, obsidian-md-ac 276→300 (trimmed Best Practices to pointer).

**Lesson:** Map by domain, use references for conditionally needed depth, and verify the changed behavior before reporting acceptance. Publication or deployment remains a separate authorized action.

## Checklist: Before Absorbing

- [ ] Does the external solution address the same class of problem as the target skill?
- [ ] Is the architecture compatible, or are you extracting only a portable principle?
- [ ] Does the change keep the common path focused and route conditional depth to a reference?
- [ ] Is there a lighter alternative such as a reference or narrow pointer?
- [ ] Is verification matched to the actual behavior and risk changed?
- [ ] Are source/canonical changes separated from runtime deployment and publication?
