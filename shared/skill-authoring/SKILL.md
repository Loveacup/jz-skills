---
name: skill-authoring
description: "Creates, audits, and improves Agent Skills with a compliance-first approach. 11-step flow: capture → grill → progressive disclosure → anti-rationalization → rule positioning → checklist → 7-dim compliance scoring → test cases → deployment-grounded audit → failure classification (DISCOVERY/OPTIMIZATION/SKILL DEFECT/EXECUTION LAPSE) → targeted revision → deploy. v3.0 absorbs SkillEvolver + EmbodiSkill (2026-05) for deployment-driven skill evolution. Use when creating, auditing, restructuring, or adding compliance elements to skills. Triggers on: 制作skill, 写skill, 优化skill, 审查skill, skill太长了, agent不遵循skill, create/improve/audit skill. DO NOT use for general documentation or one-off tasks."
version: 3.0.0
author: Hermes Agent (v3.0 absorbs SkillEvolver + EmbodiSkill insights)
license: MIT
metadata:
  hermes:
    tags: [skill-authoring, compliance, progressive-disclosure, anti-rationalization, governance]
    related_skills: [grill-with-docs, web-research-router, github, hermes-agent-skill-authoring]
---

# Skill Authoring — Compliance-First Edition v3.0

**This skill adds a compliance layer on top of existing skill-creators.** Anthropic's `skill-creator` teaches HOW to write a SKILL.md. This teaches how to make agents actually FOLLOW it. v3.0 adds deployment-grounded audit, failure classification (SkillEvolver + EmbodiSkill, 2026-05), and the Evolution Spiral.

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
| "I'll just review it myself, I wrote it" | **Self-review is NOT deployment-grounded.** SkillEvolver (2026) shows that learning signals from ANOTHER agent using the skill are 30% more reliable than self-reflection. Always deploy to a fresh agent before finalizing. |

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

Rate the skill against 7 dimensions (1-5). Target: **≥4 on all dimensions**.

| Dimension | What to check | Target |
|-----------|--------------|--------|
| **Progressive disclosure** | SKILL.md <300 lines? References/ used for depth? | ≥4 |
| **Anti-rationalization** | Red Flags table present? ≥3 specific excuse-rebuttal pairs? | ≥4 |
| **Rule positioning** | Core workflow in top 15-30%? Checklist at bottom? | ≥4 |
| **Description quality** | "Use when..." explicit? Trigger phrases + do-not included? | ≥4 |
| **Verification** | Checklist present? 3-7 actionable items? | ≥4 |
| **Runtime invocation** | Deployed to fresh agent and actually INVOKED? Silent-bypass checked? | ≥4 |
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

## Step 9: Deployment-Grounded Audit (SkillEvolver 2026)

**Do NOT self-review.** Deploy the candidate skill to a FRESH agent (different model or fresh context) and observe:

1. **Deploy** skill to a different agent/config than the authoring agent
2. **Execute** a test task that the skill should handle
3. **Observe**: Did the agent invoke the skill? Did it follow key instructions? Did it produce correct output?
4. **Classify failures** (see Step 9a)
5. **Collect ≥2 deployment signals** before revising

### Step 9a: Failure Classification (EmbodiSkill 2026)

For every failure observed during deployment, classify into exactly ONE category:

| Classification | Meaning | Action |
|:---|:---|:---|
| 🔍 **DISCOVERY** | Skill is missing content the agent needed | Add new rule/step to skill body |
| ⚡ **OPTIMIZATION** | Skill rule is valid but a better approach exists | Revise the specific rule |
| 🐛 **SKILL DEFECT** | Skill rule is wrong, incomplete, or underspecified | Correct the implicated rule |
| 🏃 **EXECUTION LAPSE** | Skill is correct but agent failed to follow it | **Do NOT change skill body.** Add emphasis to skill appendix |

**Critical rule:** Execution Lapse ≠ Skill Defect. If the agent ignored valid skill content, the skill is RIGHT — the agent failed. Preserve valid content; add an emphasis marker instead of changing the rule.

## Step 10: Targeted Revision

- **Accumulate first:** collect B=3-5 reflections before consolidating. Immediate fixes cause oscillation.
- **Consolidate:** merge overlapping reflections, remove redundant ones, resolve conflicts.
- **Revise targeted:** only change skill content IMPLICATED by the evidence. Skill content not referenced by any reflection → leave untouched.
- **Appendix update:** for Execution Lapse reflections, add emphasis markers to the skill appendix without changing the skill body.

## Step 11: Deploy

Put skill in the correct directory. Verify triggering. Follow Deployment & Sync rules at the bottom of this file.

---

## Repo Import Workflow (Existing Skill → jz-skills)

When the user says "把这个 skill 推到 GitHub" or "审查后入库" for an existing skill that's NOT yet in jz-skills:

1. **Load skill-authoring** → audit against compliance scorecard
2. **Identify gaps**: missing Red Flags? No decision tree? No verification checklist? >300 lines?
3. **Slim if needed**: move verbose sections to `references/`, add missing compliance elements
4. **Run 7-dimension scorecard with line-position evidence**: show Red Flags%, decision tree%, checklist lines-from-bottom. Present this to the user before pushing. The scorecard IS the proof that review happened. Example scorecard format above in Step 7.
5. **Sanitize**: replace home paths (`/Users/<name>/` → `~/`), emails → `<redacted>`, private IPs → `<redacted>`, API keys → `<redacted>`
6. **Copy to jz-skills**: `cp ~/.hermes/skills/<skill> jz-skills/<category>/<skill>/`
7. **Update both sync scripts**: `deploy/sync-all.sh` (forward deploy) AND `deploy/sync-back.sh` (reverse sync pairs). Missing either = broken sync.
8. **Update README badge**: increment skill count
9. **Commit**: `feat: add <skill> (compliance-reviewed, slimmed from X→Y lines)`
10. **Push**

Case studies: `references/slimming-case-studies.md` — strategic-insight-longform (513→130), voice-to-markdown (349→133), xhs-crawler (813→124), auto-diary (324→139).

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
| **Adding skill category but not updating both sync scripts** | `sync-all.sh` deploys forward but `sync-back.sh` pairs missing → reverse sync silently broken. Always update BOTH. |
| **Patched sync scripts without re-reading after each edit** | shell script `patch` operations can accidentally remove adjacent lines (e.g., merging two `cp -r` blocks removed `auto-diary` and `bilibili-video-analyzer`). After EVERY patch to a shell script: re-read the surrounding 10 lines to verify. |
| **Moving skill between directories but only updating one of two locations in sync-all.sh** | `sync-all.sh` references hermes skills in TWO places: the main `sync_hermes()` section AND the per-profile loop. Both must be updated when a skill moves (e.g., to `hermes-3S6M-profiles/common/`). |
| **Forgot to update README badge after push** | Badge shows stale count. After every skill push: increment the badge number. |
| **Applied compliance silently — didn't present the scorecard** | User can't verify the review was actually done. After modifying any skill, run the 7-dimension scorecard with line-position evidence (Red Flags at X%, decision tree at Y%, checklist at Z lines from bottom) and present it before declaring done. The scorecard IS the proof of review. |
| **Self-reviewed instead of deployment-grounded (SkillEvolver 2026)** | Self-review misses silent-bypass, overfit, and execution-lapse failures. Always deploy to a FRESH agent (different model/context) and observe actual usage before finalizing. |
| **Revised whole skill for one bug (EmbodiSkill 2026)** | Coarse whole-skill rewrites corrupt valid content. Only change skill content IMPLICATED by deployment evidence. |
| **Confused Execution Lapse with Skill Defect (EmbodiSkill 2026)** | Agent ignoring valid skill ≠ skill is wrong. Classify failures before revising: if agent didn't follow a correct rule, preserve it and add emphasis instead of changing it. |
| **Revised immediately after each failure (EmbodiSkill 2026)** | Immediate single-signal fixes cause oscillation. Accumulate B=3-5 reflections, consolidate, then revise. |
| **`cp -r` trailing slash missing when skill name matches category directory** | `cp -r shared/<name> $base/<name>/` creates nested `<name>/<name>/` when `$base/<name>/` already exists (because `cp -r source dest_dir/` copies source *into* dest_dir). For skills whose name IS the category (e.g., `github` → `$pd/github/`), use trailing slash on source: `cp -r shared/<name>/ $base/<name>/` to copy CONTENTS without nesting. Affects both `sync_hermes()` and the per-profile loop. |

---

## References

| File | Use |
|------|-----|
| `references/compliance-research.md` | Academic papers supporting compliance-first design |
| `references/anti-rationalization-catalog.md` | Full catalog of agent excuses by skill type |
| `references/example-web-research-router-v3.md` | Case study: web-research-router 500→146 line restructure |
| `references/slimming-case-studies.md` | Case studies: strategic-insight-longform (513→130) + voice-to-markdown (349→133) |
| `references/skill-evolution-research.md` | SkillEvolver + EmbodiSkill papers (2026-05): deployment-driven skill evolution |
| `references/cross-project-evaluation.md` | Decision tree for evaluating external projects before absorbing features (case studies: AnySearch, ECC, taste-skill) |
| `references/absorption-analysis.md` | When to absorb external inspiration vs when NOT to (AnySearch case study) |

---

## ✅ Author Verification Checklist (RUN BEFORE DEPLOYING)

- [ ] Did I load Anthropic `skill-creator` if this is a first-time authoring task?
- [ ] Is SKILL.md under 300 lines, with depth in `references/`?
- [ ] Is 🚨 Red Flags table in top 10% with ≥3 specific excuse-rebuttal pairs?
- [ ] Is the decision tree in top 15-30%?
- [ ] Does description include explicit "Use when..." + do-not?
- [ ] Is ✅ Verification Checklist (3-7 items) at bottom 10%?
- [ ] Did I score ≥4 on all 7 compliance dimensions (including Runtime Invocation)?
- [ ] Did I generate 8-12 should-trigger + 8-12 should-not-trigger test cases?
- [ ] Did I deploy to a FRESH agent and verify the skill was actually INVOKED (Step 9)?
- [ ] Did I classify deployment failures using the 4-type system (Step 9a)?
- [ ] Did I accumulate ≥3 reflections before consolidating and revising (Step 10)?
- [ ] If multi-profile: are Deployment & Sync rules embedded?

**Every box must honestly pass before deploying. If unchecked, fix it.**

---

> 📋 Changelog: `references/changelog.md`
> 🔄 Deployment & Sync: `references/deployment.md`
