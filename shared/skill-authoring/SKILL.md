---
name: skill-authoring
description: "Creates, audits, and improves Agent Skills with a compliance-first approach. Unlike other skill-creators that only teach 'how to write', this adds 'how to ensure agents actually follow the skill'. Use when the user wants to create a new skill, audit an existing one for compliance gaps, restructure a bloated skill into progressive disclosure, or add anti-rationalization/verification checklists. Triggers on: 制作skill, 写skill, 优化skill, 审查skill, skill太长了, agent不遵循skill, create skill, improve skill, audit skill, skill compliance. Load after Anthropic skill-creator for basic authoring, then apply this compliance layer."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skill-authoring, compliance, progressive-disclosure, anti-rationalization, governance]
    related_skills: [grill-with-docs, web-research-router, github-code-explorer, hermes-agent-skill-authoring]
---

# Skill Authoring — Compliance-First Edition

**This skill adds a compliance layer on top of existing skill-creators.** Anthropic's `skill-creator` and OpenAI's equivalent teach you HOW to write a SKILL.md. This skill teaches you how to make sure agents actually FOLLOW it.

## 🚨 Author Red Flags: Don't Ship a Skill That Won't Be Followed

| If you catch yourself thinking... | Reality check |
|-----------------------------------|---------------|
| "The instructions are clear, the agent will figure it out" | Clear ≠ followed. Agent attention windows are finite. Instructions outside the first ~200 lines may be ignored. |
| "I'll add the anti-rationalization table later" | Without it upfront, the agent will rationalize skipping the skill entirely. Add it NOW. |
| "500+ lines is fine, it's all important" | Every line past 500 reduces compliance probability. Split into references/ or accept lower compliance. |
| "I don't need a verification checklist, the steps are obvious" | Agents need explicit self-check triggers. Without a checklist, steps get skipped. |
| "This skill is for a specific task, general principles don't apply" | Compliance gaps hit ALL skill types — research routers, code reviewers, deployment scripts alike. |
| "I taught this rule to others, my own skill is fine" | **Reflexivity trap.** Meta-skills that teach compliance are the most likely to miss their own rules. Always run the Compliance Scorecard on your own skill before shipping. This very skill was caught missing its own Deployment & Sync section during self-audit. |

## Before You Start

1. **If the user has never created a skill before:** Load Anthropic's `skill-creator` first for basic YAML/progressive disclosure/description authoring. Then apply this skill's compliance layer.

2. **If auditing/improving an existing skill:** Skip Anthropic skill-creator. Go directly to the compliance checklists below.

3. **Full design → build workflow (recommended for new skills):** Load `grill-with-docs` first to clarify scope. Research existing solutions (search GitHub, papers). Then build with this compliance layer. This session demonstrated the pattern: grill scope → research 5 papers + 4 projects → build skill-authoring → self-audit → fix reflexivity gaps → deploy.

## Step 1: Progressive Disclosure Audit

A skill must follow the 3-level loading standard. Audit the skill against this table:

| Level | Content | Budget | ✅ Check |
|-------|---------|--------|---------|
| 1 | YAML frontmatter (name + description) | ~100 tokens | "Use when..." triggers are explicit, not generic |
| 2 | SKILL.md body | **<500 lines** (<5000 tokens) | If >500 lines → restructure, move content to references/ |
| 3 | `references/`, `scripts/`, `assets/` | Unlimited (lazy-loaded) | Each file referenced from SKILL.md with precise "Read when..." conditions |

**Common Level 2 bloat → fix:**

| Bloated SKILL.md contains... | Move to... | Reference from SKILL.md as... |
|------------------------------|-----------|-------------------------------|
| Detailed mode instructions (>2 paragraphs each) | `references/modes.md` | "See `references/modes.md` for full mode instructions" |
| Query examples (>3 per type) | `references/query-patterns.md` | "For query patterns, see `references/query-patterns.md`" |
| Full JSON/YAML schemas | `references/schema.md` | "Schema: `references/schema.md`" |
| Academic/research depth | `references/academic-lane.md` | "Academic lane: `references/academic-lane.md`" |
| Pitfalls beyond top 5 | `references/common-pitfalls.md` | "Full pitfalls (13 items): `references/common-pitfalls.md`" |

---

## Step 2: Add Anti-Rationalization (🚨 Red Flags)

**This is the highest-leverage compliance tool.** Add a table to the TOP of the skill (before the main content) that preempts the agent's most common excuses for skipping the skill.

### Pattern

```markdown
## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "[excuse 1]" | [rebuttal 1] |
| "[excuse 2]" | [rebuttal 2] |
| "[excuse 3]" | [rebuttal 3] |
```

### How to Generate Red Flags

For a given skill, ask: **"What would an agent say to justify NOT following this skill?"** Common patterns:

| Skill type | Common excuses |
|-----------|---------------|
| Search/router | "web_search is faster", "I know the answer", "decision tree too complex" |
| Code review | "diff is small", "I read it already", "tests pass so it's fine" |
| Deployment | "config hasn't changed", "last deploy worked", "this is a minor update" |
| Research | "I already summarized this", "let me just fetch one more thing" |

See `references/anti-rationalization-catalog.md` for the full catalog of excuses by skill type.

---

## Step 3: Critical Rule Positioning

**Rules outside the attention window don't exist.** Audit positioning:

| Check | Standard |
|-------|----------|
| Decision tree / core workflow | **Top 15-30% of file** (withink first ~75 lines for a 200-line skill) |
| Red Flags table | **Top 10%** — the very first content after frontmatter |
| Verification checklist | **Bottom 10%** — last thing agent reads before acting |
| Detailed instructions | **Below main workflow** — or in references/ |
| Reference file pointers | **Throughout body** — "For X, see `references/x.md`" |

**Why this matters:** AAAI 2026 research shows LLMs have "strong inherent biases toward certain constraint types" and instructions outside the attention window are effectively invisible. The Compliance Gap paper (arXiv 2605.01771) formalizes this as a "structural inevitability" — models default to high-reward shortcuts when procedural instructions are not frontloaded.

---

## Step 4: Add Verification Checklist

Every skill must end with a self-check. The checklist should be action items the agent can verify before returning results.

### Pattern

```markdown
## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I [primary action 1]?
- [ ] Did I [primary action 2]?
- [ ] Did I [cross-check / validate]?
- [ ] Did I [output format check]?

**If any box is unchecked, go back.**
```

### Checklist Design Rules

- **3-7 items** — more than 7 is noise, less than 3 is too vague
- **Yes/no questions** — agent can self-assess without external input
- **Actionable** — "Did I pick the right research mode?" not "Is the result good?"
- **Last thing in the file** — agent reads it immediately before returning results

---

## Step 5: Embed Deployment & Sync

If the skill will be deployed across profiles (三省六部 pattern), embed self-sync rules:

```markdown
## Deployment & Sync

After ANY update to this SKILL.md:
1. Sync to ALL Hermes profiles (dynamic discovery):
   ```bash
   for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
     dst=~/.hermes/profiles/$prof/skills/<category>/<skill-name>
     [ -d "$dst" ] && cp -r "$dst" ~/.hermes/profiles/$prof/backups/<skill-name>-$(date +%Y%m%d_%H%M%S)
     rm -rf "$dst"
     cp -r ~/.hermes/skills/<category>/<skill-name> "$dst"
   done
   ```
2. Update Obsidian documentation if this skill has one
3. `qmd update`
4. Spot-check 2-3 profiles for SKILL.md presence
```

---

## Full Skill Structure Template

A compliant skill follows this structure:

```
skill-name/
├── SKILL.md              (~150-300 lines)
│   ├── YAML frontmatter
│   ├── Overview (3-5 lines)
│   ├── 🚨 Red Flags table
│   ├── Decision tree / core workflow (top 15-30%)
│   ├── Detailed steps / modes
│   ├── Quick reference tables
│   ├── Reference file pointers
│   ├── Common pitfalls (top 5)
│   ├── Deployment & sync
│   └── ✅ Verification checklist
└── references/
    ├── <modes / patterns / schemas>.md
    └── common-pitfalls.md (full list)
```

---

## Compliance Scorecard

Rate any skill against these dimensions (1-5):

| Dimension | What to check | Target |
|-----------|--------------|--------|
| **Progressive disclosure** | SKILL.md <500 lines? References/ used for depth? | ≥4 |
| **Anti-rationalization** | Red Flags table present? ≥3 specific excuses with rebuttals? | ≥4 |
| **Rule positioning** | Core workflow in top 15-30%? Checklist at bottom? | ≥4 |
| **Description quality** | "Use when..." explicit? Trigger phrases embedded? | ≥4 |
| **Verification** | Checklist present? 3-7 actionable items? | ≥4 |
| **Deployment** | Self-sync rules included? (If multi-profile) | ≥3 |

A passing skill scores ≥4 on all dimensions.

---

## Common Pitfalls in Skill Authoring

1. **Writing for yourself instead of the agent.** The skill is read by an LLM with limited attention. Be explicit, structured, frontloaded.
2. **Assuming the agent will remember.** Attention decays. Repeat critical rules in the checklist even if mentioned earlier.
3. **Over-engineering the first draft.** Ship a 200-line skill with Red Flags + checklist. Iterate based on observed compliance failures.
4. **No negative examples.** Tell the agent what NOT to do, not just what to do. Red Flags table is the structured form of this.

---

## References

| File | Use |
|------|-----|
| `references/compliance-research.md` | Academic papers supporting compliance-first design |
| `references/anti-rationalization-catalog.md` | Full catalog of agent excuses by skill type |
| `references/example-web-research-router-v3.md` | Case study: web-research-router 500→146 line restructure |

---

## ✅ Author Verification Checklist

- [ ] Did I load Anthropic `skill-creator` if this is a first-time authoring task?
- [ ] Is SKILL.md under 500 lines, with detailed content in `references/`?
- [ ] Is the 🚨 Red Flags table in the top 10% with ≥3 specific excuse-rebuttal pairs?
- [ ] Is the core workflow / decision tree in the first 15-30% of the file?
- [ ] Does the description include explicit "Use when..." trigger phrases?
- [ ] Is there a ✅ Verification Checklist (3-7 items) at the bottom?
- [ ] If multi-profile, are Deployment & Sync rules embedded?

**If any box is unchecked, fix it before shipping.**

---

## Deployment & Sync

All skills now live in the **jz-skills git repo** as canonical source of truth:
`https://github.com/Loveacup/jz-skills`

After ANY update to this SKILL.md:

1. **Commit to git repo** (canonical source):
   ```bash
   cd ~/code/jz-skills
   git add -A && git commit -m "update skill-authoring: <what changed>"
   git push origin main
   ```

2. **Deploy to Hermes** (local → profiles):
   ```bash
   cd ~/code/jz-skills && ./deploy/sync-all.sh hermes
   ```

3. **On other machines:** `cd ~/code/jz-skills && git pull && ./deploy/sync-all.sh <platform>`

4. Update Obsidian documentation if one exists for this skill
5. `qmd update`
6. Spot-check 2-3 profiles for SKILL.md presence
