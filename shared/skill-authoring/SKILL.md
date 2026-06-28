---
name: skill-authoring
description: Make Agent Skills that actually get FOLLOWED, not just written. Use when creating, auditing, importing, slimming, or fixing a skill — especially when a skill is too long, over ~300 lines, or an agent keeps ignoring it. Adds a compliance layer on top of Anthropic's skill-creator (which teaches basic SKILL.md authoring). Triggers: 制作/写/优化/审查/导入 skill, skill 太长, agent 不遵循 skill, create / improve / audit / import / slim a skill. DO NOT use for general docs or one-off tasks.
version: 4.0.0
type: routine
license: MIT
metadata:
  hermes:
    tags: [skill-authoring, compliance, progressive-disclosure]
    related_skills: [skill-creator, grill-with-docs]
---

# Skill Authoring — make skills that get followed

> Anthropic's `skill-creator` teaches how to WRITE a SKILL.md. This teaches how to make an agent actually FOLLOW it.

## The one principle (everything below serves this)

**A skill that isn't followed is worse than none.** An agent holding `n` live rules follows them all with probability ≈ p^n — at p=0.95, ten rules → ~60%, eighty → ~2%. Adherence is not won by writing more; it's won by making the agent hold **fewer things at once**, each concrete, each where attention lands. Every token competes with the user's real request.

→ **Before adding any rule, delete or merge one.** Net live-rule count must not grow.

## 🚨 Red Flags — author excuses that kill adherence (fix on sight)

| You catch yourself thinking… | Do this instead |
|---|---|
| "It's all important, 300+ lines is fine" | Every line past the body budget lowers compliance. Move depth to `references/`. |
| "I'll add more rules so it complies" | More rules = lower p^n. **Cut n first.** Count live obligations; remove one before adding one. |
| "I'll just review it myself, I wrote it" | Self-review misses silent-bypass. Run it on a **fresh agent** and watch what it actually does. |
| "The label 『模板/示例/参考』 makes it clear" | Descriptive labels read as *optional*. Write the command: 「必须按此格式，否则=未完成」。 |
| "This is a meta/special skill, the rules don't apply here" | Reflexivity trap — meta-skills break their own rules most. **This file is held to its own standard.** |
| "More detail = more reliable" | Examples beat prose. Show 1–2 input→output pairs; cut the theory. |

## Should this be a skill at all?

```
Reusable capability, used 3+ times?  ──no──▶ Don't. A CLAUDE.md line or a one-off reply is better.
        │ yes
Overlaps an existing skill?          ──yes─▶ Improve that one. Don't fork.
        │ no
        ▼  build it ↓
```

## The flow

*Creating a skill: all 6. Auditing / slimming an existing one: skip 1–2, start at **Slim**.*

1. **Capture** — one sentence: what it does, when it fires, what success looks like. Can't say it in one sentence? Keep asking (one question at a time; read code/docs before asking the user).
2. **Basics** — first skill? Load `skill-creator` for YAML / description / structure. Then apply this compliance layer.
3. **Draft** — write the body. Then immediately…
4. **Slim** — the core craft. Apply *Progressive disclosure* + *Show-not-tell* (below) until the body is under budget.
5. **Harden** — Red Flags on top, checklist at bottom, imperative + positive phrasing, MUST only on red lines.
6. **Verify on a fresh agent** — deploy, give it a real task, watch. Did it invoke + follow? Classify any failure (below) *before* touching the skill.

## The craft (shown, not told)

**Progressive disclosure — the body is the only always-paid cost.**

| Level | Content | Budget |
|---|---|---|
| `description` | when-to-fire trigger | the ONLY discovery signal — make it specific, not generic |
| SKILL.md body | the 20% needed 80% of the time | **< ~200 lines; lower is better** |
| `references/*` | depth, one level deep | load on demand; name a load-trigger per file |

**Slimming levers — apply in order, highest yield first:**
1. **Split by audience** — environment/tool-specific ops (sync, CI, deploy) → `references/<env>-ops.md`. Biggest single win.
2. **Delete repetition** — a rule stated 5× → stated once, near the action.
3. **Ceremony → checklist** — scoring matrices / dimension rubrics don't change behavior; replace with one binary checklist.
4. **Theory → references** — research, citations, "why it works" prose. The rule stands without them.
5. **Collapse steps** — numbered steps sharing one gate or output are one move; a step that's just "then do the obvious next thing" folds into its neighbor.

**MOVE vs DELETE:** valuable to *some* task but not most → MOVE to `references/`. Redundant / pure ceremony / theory → DELETE. (So "50 pitfalls → 6" = 6 kept in body + ~34 moved + ~10 deleted as dupes.)

Keep `references/` to a handful the agent will actually load — **30+ ref files = "unfinished consolidation," not disclosure** (the agent loads ~2).

**Imperative + positive — the highest-leverage edit.** Negations and descriptive labels are followed worst:

```diff
- **汇报模板：** …                       # read as "optional reference"
+ **必须按此模板汇报，自由发挥 = 未汇报：** …   # a command
- Don't use mock data.
+ Use real data from the API.
```

**Positioning.** Red Flags in the top 10%; decision tree in the top 15%; verification checklist as the **last** thing before the agent acts. Restate the single guardrail that matters right before the output step (recency beats the middle).

**MUST budget.** Reserve MUST / ALWAYS / MANDATORY for true non-negotiables. If everything is MUST, nothing is.

**Anti-rationalization template** (top of every skill):

```markdown
## 🚨 Red Flags
| Excuse the agent will invent | Why it's wrong / do instead |
|---|---|
| "<the shortcut reasoning>" | "<close the loophole>" |
```
Generate it by asking: *"What will the agent tell itself to skip this?"*

**Verification checklist template** (bottom, copyable, binary):

```markdown
## ✅ Before returning
- [ ] Did I <primary action 1>?
- [ ] Did I <primary action 2>?
If any box is empty, go back.
```

## Before/after — this skill, applied to itself (the proof)

`skill-authoring` v3 *was* the disease it diagnoses: 365 lines, **132 table rows, 6 code blocks, 37 reference files** (agents loaded ~2), a 50-row pitfalls table — while literally containing a red flag against "adding rules to fix compliance."

v4 fix, by its own rules:
- **Split by audience** — all Hermes deploy / sync / watchdog / repo-import ops (~140 lines, the 50-row table) → `references/deploy-ops.md`, loaded only when deploying in that environment.
- **Cut n** — 50 pitfalls → 6 universal Red Flags; 11 gated steps → 6 moves; 7-dimension scoring matrix → one binary checklist.
- **Show not tell** — research-citation prose → this diff + these copyable templates.
- **Stop always-loading the catalog** — the 40-line, 37-row References table → one pointer + `references/INDEX.md`.

Result: **365 → 138 lines · table rows 132 → 22 · body live-rules ~80 → ~12** — well under the ~200 target.

More before/afters: `references/slimming-case-studies.md` — web-research-router 500→146, strategic-insight-longform 513→130, xhs-crawler 813→124.

## When a skill isn't followed: classify before fixing

| Failure | Symptom | Fix |
|---|---|---|
| **Discovery** | skill never loaded | fix the `description` triggers |
| **Comprehension** | loaded, misread | simplify wording, add an example |
| **Compliance** | understood, skipped | strengthen positioning + anti-rationalization — **don't add new rules** |
| **Capability** | followed, couldn't execute | fix the procedure or add a script |

Don't rewrite the whole skill for one failure — change only the implicated rule. If the agent ignored a **correct** rule (execution lapse), the skill is right: add emphasis, don't change it. When evolving from deployment telemetry, accumulate 3–5 signals before revising (avoids oscillation) — but a direct user fix request is itself a signal: act on it. Depth: `references/skill-evolution-research.md`.

## ✅ Before you ship (run this on your own skill)

- [ ] Did I count live rules (n) and cut one before adding one?
- [ ] Is the body under budget, with depth in `references/`?
- [ ] Red Flags in top 10%, checklist at the bottom?
- [ ] Is the `description` specific enough to fire — and to NOT over-fire?
- [ ] Imperative + positive phrasing; MUST only on red lines?
- [ ] For any format-sensitive output: at least one input→output example? (none? skip this)
- [ ] Did I run it on a **fresh agent** and watch it actually invoke + follow?

If any box is empty, fix it before shipping.

---
> Depth on demand: `references/INDEX.md` (full catalog — load by name when the subtask arises).
> Most-used: `compliance-research.md` · `anti-rationalization-catalog.md` · `slimming-case-studies.md` · `deploy-ops.md` (Hermes sync / watchdog / import / CQI).
> Changelog: `references/changelog.md`

<!-- ===================== END OF SKILL.md (drop-in replacement above this line) ===================== -->

# Restructure manifest (NOT part of SKILL.md — implementation guide)

The redesign is a *split*, not a deletion. Nothing valuable is lost; environment-specific mass moves out of the always-loaded body.

### 1. NEW `references/deploy-ops.md` ← move verbatim from current SKILL.md
Group the extracted content under these headers:
- **Repo import** ← current "Repo Import Workflow (Existing Skill → jz-skills)" (14 steps) + the slimming case-study lines.
- **Sync scripts (both directions)** ← all pitfall rows about `sync-all.sh` / `sync-back.sh` PAIRs, `cp -r` trailing-slash, skill-name=category-name mapping.
- **Watchdog recovery** ← pitfall rows about `skill-integrity-watchdog`, shadow fixes, runtime syncer drift (+ keep `references/skill-integrity-watchdog-recovery.md`).
- **Profile / multi-profile gotchas** ← `skill_view` ambiguity, profile-local source, top-level-dir-not-indexed, symlink rules.
- **CQI writeback** ← the CQI-writeback pitfall + step 14.
- **Platform / frontmatter gotchas** ← `platforms:` field rows, bundled-skill drift, `.bundled_manifest` trust.
- **Consolidation / deprecation** ← current "Skill Integration / Deprecation" section.

### 2. NEW `references/INDEX.md` ← move the current 37-row "References" table out of the body
One line per file: `name — purpose`. The body now points here instead of listing all 37.

### 3. KEEP in body (already in the v4 above)
6 universal Red Flags · should-this-be-a-skill tree · the 6-move flow · progressive-disclosure + show-not-tell craft · before/after proof · 4-type failure classification · ship checklist.

### 4. DELETE from body (re-bloat risk)
7-dimension scoring matrix (→ the binary ship checklist) · 20-row test-case table (→ optional `references/trigger-tests.md`) · all "AAAI 2026 / arXiv …" citation prose (the rule stands without the citation; keep citations in `references/compliance-research.md`).

### 5. Verify the split
`wc -l SKILL.md` ≤ ~160; grep the body for `dimension|scoring|lane|framework|audit` → near-zero; confirm every `references/*` named in the body exists; run the ship checklist on the new file itself.
