---
name: grill-with-docs
description: "Grills a plan or design against the Hermes/三省六部 domain model — challenges against CONTEXT.md glossary, cross-references with code and configs, stress-tests with concrete scenarios, and updates documentation inline as decisions crystallise. Structured 4-phase flow: load domain → walk decision tree (one question at a time via clarify+choices) → evidence challenge (read code/docs before asking) → capture & summarize. Use when the user wants to stress-test a plan, review an edict, validate a design, or explicitly invokes 'grill me' / '拷打我' / 'challenge this' / '找漏洞'. DO NOT trigger on simple unambiguous instructions or pure execution tasks."
version: 2.0.0
author: Hermes Agent (v2.0 absorbs pi/pi-grill v3.1 structured phases)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [grill, review, design-review, plan-validation, governance, 三省六部]
    related_skills: [web-research-router, github, docs-driven-design-review]
---

# Grill With Docs — Hermes/三省六部 版 v2.0

Adapted from [mattpocock/skills](https://github.com/mattpocock/skills). Original: `grill-with-docs` and `grill-me`. v2.0 absorbs pi-grill v3.1's structured 4-phase flow and evidence-challenge discipline.

Interview the user relentlessly about every aspect of a plan until shared understanding is reached. Walk down each branch of the design tree, resolving dependencies one-by-one. For each question, provide your recommended answer.

**Ask questions one at a time**, waiting for feedback on each before continuing.

**Every question MUST use `clarify` with the `choices` parameter** (max 4 options + auto-appended "Other"). Never ask as open-ended text — the user should click an option, not type. Reserve open-ended `clarify` (no choices) only for free-text follow-ups where no reasonable preset options exist.

If a question can be answered by exploring the codebase or existing documentation, do that instead of asking.

---

## 🚨 Red Flags: DO NOT BREAK THE GRILL RULES

This skill is worthless if you rationalize around its constraints. Read this before every grill session.

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "This is a simple question, I'll just type it out" | Every question MUST use `clarify` with `choices`. Typing questions as open-ended text forces the user to type back — slower, more friction. |
| "I can ask a few questions at once to save time" | One. Question. At. A. Time. Batching kills the decision-tree walk. Each question depends on the previous answer. |
| "I know what they mean, no need to challenge this" | Your job IS to challenge. Vague terms → sharpen. Conflicting terms → call out. Assumptions → test. |
| "This seems settled, let's move on" | NEVER continue until the current question is explicitly resolved (chosen, edited, or acknowledged as skipped). |
| "I'll update CONTEXT.md later" | Capture terms as they crystallize. Batched updates get forgotten. Update inline immediately. |
| "The user is busy, I shouldn't interrupt" | One question = 30 seconds. Wrong implementation = hours of rework. Grill early, not late. |
| "I'll pad my response with polite filler to sound helpful" | 🚫 **Anti-Slop.** If the response reads like generic AI output ("all things considered", "it's worth noting that"), restart. Every claim must cite a specific file, line number, config key, or doc section. No hedging without evidence. |
| "I'll list all the ambiguities at once for efficiency" | Batch questions → user only answers the last one. One at a time. |

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

## Grill Flow (4 Phases)

### Phase 1: Load Domain

Read CONTEXT.md + search for relevant ADRs (`qmd` or `search_files` for `EmpireThread_*ADR*`). Ask the user to describe what they want to build/change.

### Phase 2: Walk the Decision Tree

One question at a time, resolving each branch:

- **Challenge against glossary:** When a term conflicts with CONTEXT.md, call it out: "CONTEXT.md defines '中书省' as 拟制层, but you seem to mean 执行层 — which is it?"
- **Sharpen fuzzy language:** When terms are vague or overloaded, propose a precise canonical term: "你说'同步'——是指 profile sync、Obsidian sync、还是 skill 三文件同步？这是三件不同的事。"
- **Cross-reference with code:** When the user states how something works, check whether actual code/config agrees. Surface contradictions.
- **Stress-test with scenarios:** Invent edge cases that force precision: "如果新 profile 加了但 skill 没同步到，grill-with-docs 自己会检测到吗？"
- **Quantify vagueness:** "好一点"→"响应时间从 500ms 降到 200ms 行吗？" "快一点"→"方案A 3天但完整，方案B 1天但少30%功能，选哪个？"
- **Expose contradictions immediately:** "你说要高可用但单机部署。这两件事矛盾——你更看重哪个？"

### Phase 3: Evidence Challenge

Before asking the user a question, exhaust all verifiable sources:

- **Read code first:** "上次的方案"→ read .md or `git log` before asking
- **Check configs:** Don't ask "what model does X use" — read `config.yaml`
- **Search memory:** Check `hindsight_recall` for past decisions before re-litigating
- **Only ask when:** No code/doc/config/memory can answer it

### Phase 4: Capture & Summarize

- **Update CONTEXT.md inline:** When a term is resolved, update immediately. Don't batch — capture as they happen.
- **Offer ADRs sparingly:** Only when (1) hard to reverse, (2) surprising without context, (3) result of a real trade-off. If any criterion is missing, skip.
- **Know when to stop:** Ambiguity resolved / user calls stop / 3 consecutive questions on same topic. If hitting the limit: "上述理解对吗？可以继续了吗？"
- **Summarize:** Restate the full plan with decisions made, terms resolved, and anything left open. What was clarified + what was decided + next steps.

---

## Never Do

- NEVER ask multiple questions in one turn — one question, wait for answer, then next
- NEVER ask a question as plain text — always use `clarify` with `choices` (max 4 options + auto "Other"). Open-ended `clarify` (no choices) is only for free-text follow-ups
- NEVER accept "I'll figure that out later" without noting it as an unresolved decision
- NEVER let the user skip a question without acknowledging it was skipped
- NEVER treat CONTEXT.md as a spec, PRD, or implementation plan — it is a glossary only
- NEVER create an ADR without all three criteria met
- NEVER continue to the next question until the current one is resolved (chosen, edited, or explicitly skipped)
- NEVER exceed 3 consecutive questions on the same topic without checking: "上述理解对吗？可以继续了吗？"
- NEVER ask a question that code/docs/config could answer — evidence-challenge first

---

## ✅ Verification Checklist (RUN BEFORE ENDING EACH QUESTION)

- [ ] CHECK: Asked only ONE question this turn?
- [ ] CHECK: Used `clarify` with `choices` (max 4 options)?
- [ ] CHECK: Checked code/config/docs before asking (Phase 3: evidence challenge)?
- [ ] CHECK: Captured any resolved term in CONTEXT.md immediately?
- [ ] CHECK: Did NOT accept "I'll figure that out later" without noting it?

**Every box must honestly pass. If unchecked, go back.**

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
   - Bump `modified` timestamp
   - Update grill-with-docs version to v2.0

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
