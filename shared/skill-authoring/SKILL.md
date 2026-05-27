---
name: skill-authoring
description: "Creates, audits, and improves Agent Skills with a compliance-first approach. 9-step creation flow: grill intent → capture → progressive disclosure audit → anti-rationalization → rule positioning → verification checklist → compliance scoring (6-dimension) → test case generation → evaluate & iterate → deploy. Unlike other skill-creators that only teach 'how to write', this ensures agents actually FOLLOW the skill. Use when the user wants to create a new skill, audit an existing one for compliance gaps, restructure a bloated skill into progressive disclosure, or add anti-rationalization/verification checklists. Triggers on: 制作skill, 写skill, 优化skill, 审查skill, skill太长了, agent不遵循skill, create skill, improve skill, audit skill, skill compliance. Load after Anthropic skill-creator for basic authoring, then apply this compliance layer. DO NOT use for general documentation or one-off tasks."
version: 2.0.0
author: Hermes Agent (v2.0 absorbs pi/skill-creator v6.0)
license: MIT
metadata:
  hermes:
    tags: [skill-authoring, compliance, progressive-disclosure, anti-rationalization, governance]
    related_skills: [grill-with-docs, web-research-router, github-code-explorer, hermes-agent-skill-authoring]
---

# Skill Authoring — Compliance-First Edition v2.0

**This skill adds a compliance layer on top of existing skill-creators.** Anthropic's `skill-creator` teaches HOW to write a SKILL.md. This teaches how to make agents actually FOLLOW it. v2.0 absorbs pi/skill-creator v6.0's 9-step flow, decision tree, and test case generation.

## 🚨 Author Red Flags: Don't Ship a Skill That Won't Be Followed

| If you catch yourself thinking... | Reality check |
|-----------------------------------|---------------|
| "The instructions are clear, the agent will figure it out" | Clear ≠ followed. Attention windows are finite. >200 lines may be ignored. |
| "I'll add the Red Flags table later" | Without it upfront, the agent rationalizes skipping the skill. Add it NOW. |
| "300+ lines is fine, it's all important" | Every line past 300 reduces compliance. Split into `references/`. |
| "I don't need a verification checklist" | Agents need explicit self-check triggers. Without one, steps get skipped. |
| "This skill is special, general rules don't apply" | Compliance gaps hit ALL skill types — routers, reviewers, deployers alike. |
| "The description is good enough" | Description determines trigger rate. Not pushy enough → undertrigger. Missing do-not → overtrigger. |
| "I taught this rule to others, my own skill is fine" | **Reflexivity trap.** Meta-skills teaching compliance are most likely to miss their own rules. This very skill was caught missing its Deployment & Sync section during self-audit. Always run the Compliance Scorecard on your own skill before shipping. |

**If you caught yourself thinking any of these → stop and follow the process below.**

## 🔀 Decision Tree: Should You Create a Skill?

```
User requests skill-related operation?
├── YES → Continue
│   ├── Grill interview (one question at a time) → understand intent
│   ├── Read existing skill/code/doc → supplement context
│   └── Enter creation flow (Steps 1-9 below)
└── NO → Is this just documentation or a one-off task? → ❌ Don't create a skill
```

## Before You Start

1. **First-time skill author:** Load Anthropic `skill-creator` for basic YAML/progressive disclosure/description authoring. Then apply this compliance layer.
2. **Auditing an existing skill:** Skip Anthropic skill-creator. Jump to Progressive Disclosure Audit (Step 3) and Compliance Scorecard (Step 7).
3. **Full design→build (recommended):** Load `grill-with-docs` to clarify scope → research existing solutions → build with this compliance layer.

---

## Step 1: Capture Intent

What to build? When should it trigger? What's the expected output? What test cases are needed?

## Step 2: Grill Interview

One question at a time. Never batch. Read code/docs to answer before asking the user. Use `clarify` with `choices`.

## Step 3: Progressive Disclosure Audit

| Level | Content | Budget | ✅ Check |
|-------|---------|--------|---------|
| 1 | YAML frontmatter (name + description) | ~100 tokens | "Use when..." triggers explicit, not generic |
| 2 | SKILL.md body | **<300 lines** | If >300 → restructure, move to references/ |
| 3 | `references/`, `scripts/`, `assets/` | Unlimited (lazy) | Each file referenced with "Read when..." conditions |

**Common bloat → fix:**

| Bloated SKILL.md contains... | Move to... | Reference as... |
|------------------------------|-----------|-----------------|
| Detailed mode instructions (>2 paragraphs) | `references/modes.md` | "See `references/modes.md`" |
| Query examples (>3 per type) | `references/query-patterns.md` | "For query patterns: `references/query-patterns.md`" |
| Full JSON/YAML schemas | `references/schema.md` | "Schema: `references/schema.md`" |
| Academic/research depth | `references/academic-lane.md` | "Academic lane: `references/academic-lane.md`" |
| Pitfalls beyond top 5 | `references/common-pitfalls.md` | "Full pitfalls: `references/common-pitfalls.md`" |

## Step 4: Add Anti-Rationalization (🚨 Red Flags)

**Highest-leverage compliance tool.** Add a table at the TOP of the skill that preempts common excuses.

```markdown
## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "[excuse 1]" | [rebuttal 1] |
```

**How to generate:** Ask "What would an agent say to justify NOT following this skill?" See `references/anti-rationalization-catalog.md` for the full catalog by skill type.

## Step 5: Critical Rule Positioning

**Rules outside the attention window don't exist.**

| Check | Standard |
|-------|----------|
| Decision tree / core workflow | **Top 15-30%** of file |
| Red Flags table | **Top 10%** — first content after frontmatter |
| Verification checklist | **Bottom 10%** — last thing agent reads before acting |
| Detailed instructions | Below main workflow, or in `references/` |

Why: LLMs have "strong inherent biases toward certain constraint types" (AAAI 2026). Instructions outside the attention window are effectively invisible.

## Step 6: Add Verification Checklist

```markdown
## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I [primary action 1]?
- [ ] Did I [primary action 2]?
...
**If any box is unchecked, go back.**
```

Rules: **3-7 items**, yes/no questions, actionable, last thing in the file.

## Step 7: Compliance Scoring

Rate the skill against 6 dimensions (1-5). Target: **≥4 on all dimensions**.

| Dimension | What to check | Target |
|-----------|--------------|--------|
| **Progressive disclosure** | SKILL.md <300 lines? References/ used for depth? | ≥4 |
| **Anti-rationalization** | Red Flags table present? ≥3 specific excuse-rebuttal pairs? | ≥4 |
| **Rule positioning** | Core workflow in top 15-30%? Checklist at bottom? | ≥4 |
| **Description quality** | "Use when..." explicit? Trigger phrases + do-not included? | ≥4 |
| **Verification** | Checklist present? 3-7 actionable items? | ≥4 |
| **Deployment** | Self-sync rules included? (If multi-profile) | ≥3 |

See `references/compliance-research.md` for detailed scoring methodology.

## Step 8: Generate Test Cases

8-12 **should-trigger** scenarios + 8-12 **should-not-trigger** scenarios. Examples:

| Scenario | Should trigger? | Why |
|----------|:-:|-----|
| "搜一下 React 19 新特性" | ✅ | Matches "搜" trigger |
| "帮我读一下 README.md" | ❌ | Read local file, not search |
| ... | | |

Save full test cases to `references/trigger-tests.md`.

## Step 9: Evaluate & Iterate

- Fix over/under-triggering based on test cases
- If ≥5 batch edits: re-read full file to check structural integrity
- Re-run Compliance Scorecard after each major edit

## Step 10: Deploy

Put skill in the correct directory. Verify triggering. Follow Deployment & Sync rules at the bottom of this file.

---

## Pitfalls

| Trap | Consequence |
|------|-------------|
| Description not pushy enough | Undertriggering — skill never loads |
| Missing do-not in description | Overtriggering — loads on irrelevant tasks |
| Body >300 lines | Content beyond line 300 ignored by agent |
| Only explaining WHAT, not WHY | Agent can't prioritize |
| Inconsistent terminology | Agent confuses similar concepts |
| No test cases | Changing description breaks triggering silently |
| Vague name | Use gerund form (e.g., `recover-hindsight-mcp`) |
| Creating a skill for a one-off task | Wastes tokens, pollutes skill list |
| Batch-interviewing the user | User only answers the last question |
| Asking questions that code/docs could answer | Wastes user time, reduces trust |
| Missing Red Flags table | ⚠️ MANDATORY. Without it, skill is dead on arrival |
| Decision tree buried too deep | Must be in top 20% of body |
| Batch-patching without re-check | ≥5 edits → re-read full file |
| Writing for humans instead of agents | The agent is the reader; humans are reviewers |
| No verification checklist | Agent has no self-check mechanism |

---

## References

| File | Use |
|------|-----|
| `references/compliance-research.md` | Academic papers supporting compliance-first design |
| `references/anti-rationalization-catalog.md` | Full catalog of agent excuses by skill type |
| `references/example-web-research-router-v3.md` | Case study: web-research-router 500→146 line restructure |

---

## ✅ Author Verification Checklist (RUN BEFORE DEPLOYING)

- [ ] Did I load Anthropic `skill-creator` if this is a first-time authoring task?
- [ ] Is SKILL.md under 300 lines, with depth in `references/`?
- [ ] Is 🚨 Red Flags table in top 10% with ≥3 specific excuse-rebuttal pairs?
- [ ] Is the decision tree in top 15-30%?
- [ ] Does description include explicit "Use when..." + do-not?
- [ ] Is ✅ Verification Checklist (3-7 items) at bottom 10%?
- [ ] Did I score ≥4 on all 6 compliance dimensions?
- [ ] Did I generate 8-12 should-trigger + 8-12 should-not-trigger test cases?
- [ ] If multi-profile: are Deployment & Sync rules embedded?

**If any box is unchecked, fix it before deploying.**

---

## Deployment & Sync

All skills now live in the **jz-skills git repo** as canonical source of truth:
`https://github.com/Loveacup/jz-skills`

### Repository Structure

```
jz-skills/
├── shared/          ← Cross-platform skills (Hermes + CC + pi)
├── hermes/          ← Hermes-specific (三省六部, trading, wiki)
├── cc/              ← Claude Code specific
├── pi/              ← pi specific
└── deploy/
    ├── sync-all.sh   ← Forward: repo → local agents
    └── sync-back.sh  ← Reverse: local agents → repo
```

### After ANY update to this SKILL.md:

1. **Commit to git repo** (canonical source)
2. **Deploy to Hermes:** `cd ~/code/jz-skills && ./deploy/sync-all.sh hermes`
3. **On other machines:** `git pull && ./deploy/sync-all.sh <platform>`
4. Update Obsidian documentation if one exists
5. `qmd update`
6. Spot-check 2-3 profiles for SKILL.md presence
