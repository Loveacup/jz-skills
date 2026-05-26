---
name: grill-with-docs
description: "Grills a plan or design against the Hermes/三省六部 domain model — challenges against CONTEXT.md glossary, cross-references with code and configs, stress-tests with concrete scenarios, and updates documentation inline as decisions crystallise. Use when the user wants to stress-test a plan, review an edict, or validate a design against the system's language and documented decisions."
version: 1.2.0
author: Hermes Agent (adapted from mattpocock/skills)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [grill, review, design-review, plan-validation, governance, 三省六部]
    related_skills: [web-research-router, github-code-explorer, docs-driven-design-review]
---

# Grill With Docs — Hermes/三省六部 版

Adapted from [mattpocock/skills](https://github.com/mattpocock/skills). Original: `grill-with-docs` and `grill-me`.

Interview the user relentlessly about every aspect of a plan until shared understanding is reached. Walk down each branch of the design tree, resolving dependencies one-by-one. For each question, provide your recommended answer.

**Ask questions one at a time**, waiting for feedback on each before continuing.

**Every question MUST use `clarify` with the `choices` parameter** (max 4 options + auto-appended "Other"). Never ask as open-ended text — the user should click an option, not type. Reserve open-ended `clarify` (no choices) only for free-text follow-ups where no reasonable preset options exist.

If a question can be answered by exploring the codebase or existing documentation, do that instead of asking.

---

## 🚨 Red Flags: DO NOT BREAK THE GRILL RULES

This skill is worthless if you rationalize around its constraints. Read this before every grill session.

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "This is a simple question, I'll just type it out" | Every question MUST use `clarify` with `choices`. Typing questions as open-ended text forces the user to type back — slower, more friction, violates the core promise of this skill. |
| "I can ask a few questions at once to save time" | One. Question. At. A. Time. Batching kills the decision-tree walk. Each question depends on the previous answer. |
| "I know what they mean, no need to challenge this" | Your job IS to challenge. Vague terms → sharpen. Conflicting terms → call out. Assumptions → test. If you don't grill, this skill does nothing. |
| "This seems settled, let's move to the next branch" | NEVER continue until the current question is explicitly resolved (chosen, edited, or acknowledged as skipped). |
| "I'll update CONTEXT.md later" | Capture terms as they crystallize. Batched updates get forgotten. Update inline immediately. |

**If you caught yourself thinking any of these → re-read the Never Do list and restart the current question.**

---

## Domain Awareness

### CONTEXT.md (the glossary)

The system's domain model lives at:

```
Obsidian: 20-Areas/10_AI实践/三省六部_Hermes/CONTEXT.md
```

This file defines all canonical terms: 三省六部 roles, skill names, research modes, GitHub exploration layers, memory hierarchy, deployment concepts, machine roles, EmpireThread concepts.

Before every grilling session, **read CONTEXT.md** to load the current glossary.

### ADRs (Architecture Decision Records)

EmpireThread ADRs live in the Obsidian vault (discover via `qmd` or filesystem search). Format: `EmpireThread_关键决策_ADR` or `EmpireThread_*_ADR*`.

### Code and config to cross-reference

The "code" to verify against includes:

| Surface | Location | What to check |
|---------|----------|---------------|
| Skill files | `~/.hermes/skills/*/SKILL.md` | Are skill names/descriptions consistent with terms used in the plan? |
| Profile configs | `~/.hermes/profiles/*/config.yaml` | Do profile roles match what the plan assumes? |
| MCP config | `~/.hermes/config.yaml` `mcp_servers:` | Are referenced tools actually available? |
| Cron jobs | `hermes cron list` | Does the plan conflict with existing schedules? |
| Memory | `hindsight_recall` | Are there relevant past decisions? |

---

## During the Session

### Challenge against the glossary

When the user uses a term that conflicts with existing language in CONTEXT.md, call it out immediately: "CONTEXT.md defines '中书省' as 拟制层, but you seem to mean 执行层 — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term: "你说'同步'——是指 profile sync、Obsidian sync、还是 skill 三文件同步？这是三件不同的事。"

### Cross-reference with code

When the user states how something works, check whether the actual code/config agrees. If you find a contradiction, surface it: "你说 cron job X 用 deepseek，但 config 里显示它是默认模型——需要更新吗？"

### Discuss concrete scenarios

Stress-test with specific edge cases. Invent scenarios that force precision about boundaries:
- "如果新 profile 加了但 skill 没同步到，grill-with-docs 自己会检测到吗？"
- "如果 CONTEXT.md 和某个 skill 的 SKILL.md 对同一个术语定义不一致，以谁为准？"

### Update CONTEXT.md inline

When a term is resolved, update `20-Areas/10_AI实践/三省六部_Hermes/CONTEXT.md` immediately. Don't batch — capture as they happen. CONTEXT.md is a glossary only, never a spec or scratch pad.

### Offer ADRs sparingly

Only create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR.

---

## Never Do

- NEVER ask multiple questions in one turn — one question, wait for answer, then next
- NEVER ask a question as plain text — always use `clarify` with `choices` (max 4 options + auto "Other"). Open-ended `clarify` (no choices) is only for free-text follow-ups
- NEVER accept "I'll figure that out later" without noting it as an unresolved decision
- NEVER let the user skip a question without acknowledging it was skipped
- NEVER treat CONTEXT.md as a spec, PRD, or implementation plan — it is a glossary only
- NEVER create an ADR without all three criteria met
- NEVER continue to the next question until the current one is resolved (chosen, edited, or explicitly skipped)

---

## Session Flow

1. **Load domain:** Read CONTEXT.md + search for relevant ADRs (`qmd` or `search_files` for `EmpireThread_*ADR*`)
2. **Understand the plan:** Ask the user to describe what they want to build/change
3. **Walk the decision tree:** One question at a time, resolving each branch:
   - Does this conflict with existing glossary terms?
   - Does this conflict with existing ADRs?
   - Does the code/config support what's being proposed?
   - Are there edge cases the plan doesn't cover?
4. **Capture decisions:** Update CONTEXT.md for resolved terms, offer ADRs for irreversible decisions
5. **Summarize:** Restate the full plan with decisions made, terms resolved, and anything left open

---

## Deployment & Sync

**After ANY update to this SKILL.md, you MUST:**

1. **Sync to ALL Hermes profiles** — discover and sync dynamically:
   ```bash
   for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
     dst=~/.hermes/profiles/$prof/skills/governance/grill-with-docs
     [ -d "$dst" ] && cp -r "$dst" ~/.hermes/profiles/$prof/backups/grill-with-docs-$(date +%Y%m%d_%H%M%S)
     rm -rf "$dst"
     cp -r ~/.hermes/skills/governance/grill-with-docs "$dst"
   done
   ```

2. **Sync Obsidian documentation** — update `00-Inbox/工具制作_Hermes检索总控与GitHub源码探索_三省六部体系_20260526.md`:
   - Add grill-with-docs to the skill inventory
   - Add CONTEXT.md creation to knowledge base updates
   - Bump `modified` timestamp

3. **Update CONTEXT.md** — ensure `grill-with-docs` is listed in the glossary under "核心 skill"

4. **Update qmd index:** `qmd update`

5. **Verify:** Spot-check 2-3 profiles for SKILL.md presence + check that CONTEXT.md contains the grill-with-docs entry.

```
User: /grill-with-docs I want to add a new 兵部 profile for security scanning

Agent: [reads CONTEXT.md, searches for security-related ADRs]

Agent: CONTEXT.md defines 兵部 as "安全、权限、破坏性操作" — is this new profile an additional 兵部 instance, or replacing the existing one?

User: Additional. It runs nightly scans.

Agent: [cross-references cron jobs] There's already a sync-memory-to-regent cron running every 360 minutes. Will your nightly scan conflict with it, or should they be staggered?

... [continues one question at a time]
```

---

## ✅ Verification Checklist (RUN BEFORE ENDING EACH QUESTION)

- [ ] Did I ask only ONE question this turn?
- [ ] Did I use `clarify` with `choices` (max 4 options)?
- [ ] Did I check code/config before asking (not ask blindly)?
- [ ] Did I capture any resolved term in CONTEXT.md immediately?
- [ ] Did I NOT accept "I'll figure that out later" without noting it?

**If any box is unchecked, go back.**
