---

name: skill-authoring
description: "Creates, audits, imports, and improves Agent Skills with a compliance-first approach. Also routes centralized SkillHub operations so agents do not read the full Obsidian governance project by default. 11-step flow: capture → grill → progressive disclosure → anti-rationalization → rule positioning → checklist → 7-dim compliance scoring → test cases → deployment-grounded audit → failure classification → targeted revision → deploy. Use when creating, auditing, importing GitHub skills, restructuring skills, updating SkillHub metadata, or adding compliance elements to skills. Triggers on: 制作skill, 写skill, 优化skill, 审查skill, 导入skill, skill太长了, agent不遵循skill, create/improve/audit/import skill. DO NOT use for general documentation or one-off tasks."
type: routine
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
3. **Centralized SkillHub operation:** Do not read the full Obsidian project. Read `references/agent-skillhub-context-map.md`, then only the task-specific files it names. Use `references/agent-skillhub-workflow.md` for new skill, GitHub import, pool classification, runtime exposure, or Obsidian writeback.
4. **Full design→build (recommended):** Load `grill-with-docs` to clarify scope → research existing solutions → build with this compliance layer.

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
5. **Sanitize**: run `sync-back.sh` (replaces home paths, emails, private IPs, API keys) → then run the full 28-pattern manual audit from `references/desensitization-audit.md` to catch what sync-back.sh misses (vault names, personal names in content, cron IDs, app instance IDs, ports).
6. **Profile-local source check**: if the source skill lives under `~/.hermes/profiles/<profile>/skills/`, `sync-back.sh` may not see it because it reads default `~/.hermes/skills`. Use the profile-local import + staged-only audit pattern in `references/repo-import-profile-local-and-staged-audit.md`; do not mutate the live profile just to make sync-back convenient.
7. **Copy to jz-skills**: `cp ~/.hermes/skills/<skill> jz-skills/<category>/<skill>/` OR `rsync -a --delete <actual-profile-skill-dir>/ jz-skills/<layer>/<skill>/` for profile-local sources.
8. **Update both sync scripts**: `deploy/sync-all.sh` (forward deploy) AND `deploy/sync-back.sh` (reverse sync pairs). Missing either = broken sync.
9. **Update README badge/tree**: increment skill count and add any newly visible skill rows.
10. **Commit carefully**: if the repo has unrelated dirty files, stage explicit paths only and audit `git diff --cached --name-status` before committing. Use a bilingual conventional commit such as `feat: add <skill> / 新增 <skill>`.
11. **Push**
12. **Sync to all active Hermes profiles**: after push, immediately sync to regent and other profiles. `rsync -av --delete ~/.hermes/skills/<path>/ ~/.hermes/profiles/<prof>/skills/<path>/`. Don't wait for the user to remind you.
13. **Verify no stale references**: grep for old names across all skills.: if this skill absorbed/deleted old skills, run `grep -rn "<old-skill-name>" ~/.hermes/skills/ --include="*.md" | grep -v "replaces:" | grep -v "consolidation-case-study"` to catch every remaining reference. Fix ALL before declaring done. Also check jz-skills repo: `grep -rn "<old-name>" ~/code/jz-skills/ --include="*.md"`.

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
| **Editing protected bundled/hub-installed skills** | User may ask to update the skill library after a session where the only directly relevant loaded skill is bundled (e.g. `hermes-agent`). Do NOT patch protected skills. First look for an existing user-owned umbrella skill that covers the class; add a concise `references/` file and one-line SKILL.md pointer there. If no unprotected umbrella fits, say `Nothing to save.` instead of creating a narrow duplicate. |
| Batch-interviewing the user | User only answers the last question |
| Asking questions that code/docs could answer | Wastes user time, reduces trust |
| Missing Red Flags table | ⚠️ MANDATORY. Without it, skill is dead on arrival |
| Decision tree buried too deep | Must be in top 20% of body |
| Batch-patching without re-check | ≥5 edits → re-read full file |
| **Writing for humans instead of agents** | The agent is the reader; humans are reviewers |
| **Single-skill category with vague name** | Don't create category dirs for one skill. See `references/category-naming-pitfall.md`. |
| **No verification checklist** | Agent has no self-check mechanism |
| **Adding skill category but not updating both sync scripts** | `sync-all.sh` deploys forward but `sync-back.sh` pairs missing → reverse sync silently broken. Always update BOTH. |
| **Patched sync scripts without re-reading after each edit** | shell script `patch` operations can accidentally remove adjacent lines (e.g., merging two `cp -r` blocks removed `auto-diary` and `bilibili-video-analyzer`). After EVERY patch to a shell script: re-read the surrounding 10 lines to verify. |
| **Moving skill between directories but only updating one of two locations in sync-all.sh** | `sync-all.sh` references hermes skills in TWO places: the main `sync_hermes()` section AND the per-profile loop. Both must be updated when a skill moves (e.g., to `hermes-3S6M-profiles/common/`). |
| **Forgot to update README badge after push** | Badge shows stale count. After every skill push: increment the badge number. |
| **Applied compliance silently — didn't present the scorecard** | User can't verify the review was actually done. After modifying any skill, run the 7-dimension scorecard with line-position evidence (Red Flags at X%, decision tree at Y%, checklist at Z lines from bottom) and present it before declaring done. The scorecard IS the proof of review. |
| **Self-reviewed instead of deployment-grounded (SkillEvolver 2026)** | Self-review misses silent-bypass, overfit, and execution-lapse failures. Always deploy to a FRESH agent (different model/context) and observe actual usage before finalizing. |
| **Revised whole skill for one bug (EmbodiSkill 2026)** | Coarse whole-skill rewrites corrupt valid content. Only change skill content IMPLICATED by deployment evidence. |
| **Descriptive labels don't enforce — 「汇报模板：」≠ 命令** | Section headers like 「模板：」「示例：」「参考格式：」 are read as reference material, not mandatory instructions. Agent rationalizes: "this is just an example." **Fix**: (1) rewrite label as imperative — 「必须严格按此格式，不按模板 = 未完成」; (2) add Execution Lapse pre-interception blockquote; (3) bind format requirement to the Core Rule. Case study: `references/template-vs-command.md`. |
| **Confused Execution Lapse with Skill Defect (EmbodiSkill 2026)** | Agent ignoring valid skill ≠ skill is wrong. Classify failures before revising: if agent didn't follow a correct rule, preserve it and add emphasis instead of changing it. |
| **Revised immediately after each failure (EmbodiSkill 2026)** | Immediate single-signal fixes cause oscillation. Accumulate B=3-5 reflections, consolidate, then revise. |
| **`cp -r` trailing slash missing when skill name matches category directory** | `cp -r shared/<name> $base/<name>/` creates nested `<name>/<name>/` when `$base/<name>/` already exists (because `cp -r source dest_dir/` copies source *into* dest_dir). For skills whose name IS the category (e.g., `github` → `$pd/github/`), use trailing slash on source: `cp -r shared/<name>/ $base/<name>/` to copy CONTENTS without nesting. Affects both `sync_hermes()` and the per-profile loop. |
| **sync-back.sh PAIR herm_path wrong when skill name = category name** | When the skill name matches the category directory name (e.g., `github` skill lives in `~/.hermes/skills/github/`), the PAIR should be `"shared/github|github"` — NOT `"shared/github|github/github"`. The herm_path is the local path relative to `~/.hermes/skills/`, so a skill that IS the github directory maps to just `github`. Contrast with a subcategory skill like `grill-with-docs` which maps to `governance/grill-with-docs`. Symptom: sync-back.sh dry-run says `source not found — skipped`. |
| **Multi-profile skill name ambiguity — `skill_view()` fails with 'Ambiguous skill name'** | When a profile's local `skills/` contains a symlink or real copy of a skill that also exists in `external_dirs`, `skill_view(name)` finds TWO copies and refuses to guess. **Workarounds** (temporary): (a) `read_file` with absolute path instead of `skill_view`; (b) for `skill_manage` passes, use `cross_profile=True`; (c) for bulk writes use `terminal` to bypass the guard. **Permanent fix**: (1) identify the DUPLICATE SOURCE — common culprits are plugin-created symlinks (e.g. 3s6m `skill_sync.py`), stale `sync_skills` artifacts, or manual copies; (2) check if the source now has skip logic (newer `skill_sync.py` reads `external_dirs` and skips duplicates — old symlinks were created before skip was added); (3) delete ONLY the profile-local entry using `find -maxdepth 1 -type l -name <name> -delete` for symlinks or `rm -rf` for real dirs (⚠️ `rm -rf */` follows symlinks and destroys source files — use maxdepth guard); (4) verify the symlink won't be recreated on next session start by testing the creation source's skip logic in dry-run mode; (5) re-run `skill_view(name)` to confirm clean. |
| **Watchdog shadow fix: DELETE, don't symlink — then update baseline** | The `skill-integrity-watchdog` cron job flags BOTH real-dir copies (CRITICAL a) AND symlinks (CRITICAL d) when a profile-local entry shadows a pool skill. Converting a real-dir to a symlink just moves the alert from (a) to (d) — the fix is to DELETE the local entry entirely (pool `external_dirs` already provides it) and then run `python3 scripts/skill-integrity-watchdog.py --update-baseline` to reset. Symlinks into the pool are ALSO considered shadowing because they create ambiguous-skill-name conflicts (skill_sync is supposed to skip pool-covered skills, but pre-existing symlinks evade the guard). Case: 2026-06-03 — de-slop, news-assembly, source-verification, tts-manager, morning-news-briefing. |
| **Watchdog shadows recur after deletion — patch the runtime syncer, not just repo** | If profile-local shadows reappear after cleanup, check which `tools/skills_sync.py` is imported at runtime. Hermes may use `venv/lib/python*/site-packages/tools/skills_sync.py`, which can lag behind the repo copy and lack `.no-bundled-skills` opt-out support. Root fix: update/reinstall the runtime syncer, create opt-out markers for profiles whose skills come from `external_dirs`, delete local shadows, verify `sync_skills()` skips, then run local watchdog + cron. If watchdog warns a pool skill disappeared, search profile/lane copies and restore the most complete copy before changing the baseline. See `references/skill-integrity-watchdog-recovery.md`. |
| **Consolidated/deleted old skills without global grep for stale references** | After deleting absorbed skills, other skills' `related_skills`, `description`, decision trees, and reference files may still point to the OLD skill names. Run `grep -rn "<old-name>" ~/.hermes/skills/ --include="*.md" | grep -v "replaces:"` to find every remaining reference. Fix ALL of them before declaring done. Case study: `github-code-explorer` → `github` consolidation left 7 stale references across web-research-router, grill-with-docs, and skill-authoring. |
| **Patch fuzzy-match destroyed file content — old_string didn't match precisely** | When `patch` can't find an exact match, fuzzy matching can replace a MUCH larger block than intended (e.g., 188-line file → 54-line file because the tool matched a near-but-wrong section and rewrote everything from there). **Symptoms**: file suddenly much shorter, unrelated content gone. **Recovery**: (1) `cp` from known-good source (jz-skills git repo, or another profile copy); (2) verify `wc -l` matches expected; (3) re-read fresh file from disk; (4) re-patch using exact strings copy-pasted from the fresh read. **Prevention**: after ANY `patch` to a reference file, `wc -l` and spot-check the first line to confirm the file wasn't replaced wholesale. Case study: mac-doctor cron-module.md corrupted during cross-profile patch (2026-05-31). |
| **Premature conclusion without reconciling contradictory evidence** | You tested X and it failed. Someone else tested X and it worked. Declaring "X is dead, don't try" burns trust and wastes opportunity. The right response: flag the contradiction, propose investigation steps, and suspend conclusion until reconciled. Case study: Scrapling WeChat — own tests failed (0/5) but 张睿 succeeded; premature "放弃" before reconciling. |
| **Assumed integration exists without verifying** | A technical analysis document describes an integration design. You read it and assume it's already implemented. User corrects: it was never built, never deployed. Fix: when reading a design/proposal document, explicitly CHECK whether it describes current state or aspirational state. Ask "is this already live, or is this a plan?" before referencing it as fact. Case study: aihot+xhs-tech-writer.
| **Bundled skill locally modified — version drift undetected** 🆕 | A skill shipped with Hermes (in `hermes-agent/skills/`) was locally modified by a governance system that's now decommissioned — version number bumped, hundreds of lines added with stale references. The skill loads and triggers normally, but its content is wrong. Version string alone is insufficient (the local version was bumped to 3.6.0 while upstream is 3.0.0 — version NUMBERS can be modded too). **Fix**: compare sha256 + git. Detection recipe in `references/bundled-skill-drift-detection.md`. Case study: kanban-orchestrator — 66 governance residues in local 3.6.0 vs upstream clean 3.0.0 (2026-06-03). |
| **sync-back.sh passed but repo still contains sensitive data** 🆕 | sync-back.sh auto-sanitizes `$HOME/` → `~/`, emails, private IPs, and API keys — but misses Obsidian vault names (contain real name in subpath), personal names in content (e.g., PDF footers, TTS voice names), cron job IDs, app instance/bundle IDs (e.g., DingTalk `5ZSL2CJU2T.com.dingtalk.mac`), local service ports (`127.0.0.1:6152`), and hardcoded usernames in scripts that weren't run through the sanitize pipeline. **Fix**: after sync-back, run the full 28-pattern audit from `references/desensitization-audit.md` before committing. Case study: jz-skills repo 2026-06-06 — 8 findings across 4 severity levels despite sync-back.sh running. |
| **Replaced plan content instead of appending** | User said "加到计划里" (add to the plan). You used `patch` to replace a section with new content. The old_string and new_string happened to be identical so the tool rejected it — but the intent was wrong from the start. **Fix**: when user says 加/追加/补充, APPEND — read the file, find insertion point, add AFTER the target section. Don't look for text to replace. |
| **Over-automated CQI MVP before the log/manual loop is stable** | A CQI plan jumped straight to cron/Kanban/A2A/fleet inspection as Phase 1, but the intended MVP was log automation → CC-mediated CQI Plan Writer → fresh CC audit → writeback. **Fix**: keep Phase 1 log-driven and manually gated; move cron/Kanban/A2A/continuous inspection to Phase 2. For the detailed pattern, see `references/log-driven-cqi-mvp.md`. |
| **Sub-agent injected P(N+1) deps into P(N) deliverables** 🆕 | A sub-agent (CC) working on Phase N inserted Phase N+1 dependencies (APIs/sources not yet built or tested) into Phase N deliverables. Detection: diff references tools not in phase plan; referenced file 404; degradation table admits unreliability. Fix: gate new deps against phase plan. No pre-flight test → stay auxiliary. Full case: `references/cross-phase-dependency-injection.md`. |
| **platforms field causes unsupported even with whitelisted values** 🆕 | Hermes PLATFORM_MAP hardcodes macos/linux/windows. Non-whitelist values (cron, telegram) always fail. BUT even whitelisted values can trigger unsupported on valid platforms (2026-06-07: platforms: [macos, linux] on macOS → skill_view returned unsupported). Safer fix: omit platforms: entirely unless the skill genuinely cannot run on some OSes. | → skill permanently unsupported** 🆕 | Hermes `agent/skill_utils.py` hardcodes `PLATFORM_MAP = {"macos": "darwin", "linux": "linux", "windows": "win32"}`. Any other value (e.g., `cron`, `telegram`) is NOT mapped — compared raw against `sys.platform` → always FAILS → `readiness_status: unsupported`. **Fix**: only use `macos`, `linux`, or `windows` in the `platforms:` frontmatter field. Never invent values like `cron` or `telegram`. |
| **Trusted `.bundled_manifest` as source of truth for skill origins** 🆕 | `.bundled_manifest` is a local snapshot — can be stale, incomplete, or out of sync with installed Hermes version. Always compare against `~/.hermes/hermes-agent/skills/` + `optional-skills/`. See `references/skill-origin-classification.md`. Case: 2026-06-07 audit — manifest had 60 entries, but Hermes core ships 74. |
| **Skill deployed to `skills/` top-level directory → never indexed** 🆕 | Hermes skill indexer scans ONLY category subdirectories (e.g., `productivity/`, `devops/`). A skill directory placed directly under `skills/` (no parent category) is invisible — `skill_view` returns "not found" even though files exist on disk. **Fix**: always deploy skills into a category subdirectory. For cross-profile symlinks: `ln -s ~/.hermes/skills/<category>/<name> ~/.hermes/profiles/<prof>/skills/<category>/<name>` — NOT to the profile's `skills/` top level. Case: morning-news-briefing 2026-06-03 P0 fix. |
| **User says “find/pull a skill from GitHub” but repo has untracked local skill dir** 🆕 | In a local skill hub repo, `git pull` can be up to date while the requested skill exists only as `?? <layer>/<skill>/` in the working tree. GitHub code search and `origin/main` will show nothing, but the usable source is still present locally. **Fix**: check three planes separately before concluding: (1) remote tracked tree (`git ls-tree origin/main`, remote branches, `gh search code --repo ...`); (2) local working tree including untracked dirs (`git status --porcelain`, path scan); (3) deployed Hermes index (`skill_view`). If deploying from an untracked local draft, say it is “deployed from local working tree, not pulled from remote”, rsync to `~/.hermes/skills/<category>/<skill>/`, then verify with `skill_view`. If the user wants it truly on GitHub, follow repo import workflow: sync mapping + README + audit + commit/push. |

---

## 🔀 Skill Integration / Deprecation（子 skill 吸收回主体或清理）

当某个独立 skill 被发现是另一 skill 的子组件时，按以下流程整合或清理：

### 流程

1. **全仓库依赖分析** — `grep -rl '<skill-name>' hermes/ shared/ --include='*.md'` 扫描所有引用者，确认依赖面不是单一的
2. **判断是否共享组件** — 若被 2+ 个主体 skill 调用 → 保留独立（DRY 合理）。若只被 1 个主体调用 → 候选吸收
3. **出整合方案** — 操作细节 → 主体 `references/` 新文件；脚本 → 主体 `scripts/`；主体 SKILL.md 引用更新；被吸收 skill 删除
4. **同步脚本清理** — 检查并更新 `deploy/sync-all.sh`（正向）和 `deploy/sync-back.sh`（反向）中的路径映射
5. **README 更新** — 技能计数、目录树、描述行
6. **部署端侦查** — 用 `find ~/.hermes -type d -name <skill>` 扫描所有副本；活跃加载路径执行删除+同步，沙盒/归档/venv 跳过
7. **qmd update** — 删完 skill 后刷新向量索引

### Pitfalls

- **不要假设"子 skill 只被一个主体用"** — 先跑全仓库 grep，可能发现是共享闸门（如 source-verification 被 morning-news + news-assembly 共用，保留独立）
- **sed 在格式化 README 中不可靠** — Python 行级过滤更稳：`[line for line in lines if 'skill-name' not in line]`
- **不要顺手做无关修复** — 发现既有死引用（如 WRR 的 code-explorer.md）记下即可，不混入本次范围
- **git 不擅自提交** — 所有改动留在工作区，等用户确认
- **整合后清理孤儿子目录** — 整合伞形 skill 后，旧独立 skill 目录不会自动从部署池删除。sync-all.sh 只增不删。使用 watchdog + `references/post-consolidation-cleanup.md` 工作流检测和清理孤儿。

## 📦 References

| File | Use |
|------|-----|
| `references/compliance-research.md` | Academic papers supporting compliance-first design |
| `references/anti-rationalization-catalog.md` | Full catalog of agent excuses by skill type |
| `references/example-web-research-router-v3.md` | Case study: web-research-router 500→146 line restructure |
| `references/slimming-case-studies.md` | Case studies: strategic-insight-longform (513→130) + voice-to-markdown (349→133) |
| `references/skill-evolution-research.md` | SkillEvolver + EmbodiSkill papers (2026-05): deployment-driven skill evolution |
| `references/consolidation-case-study.md` | Multi-skill consolidation pattern (8→1): shared state, decision tree, governance |
| `references/post-consolidation-cleanup.md` | 🆕 Post-consolidation orphan detection & cleanup: watchdog triage, pool deletion, sync script fixes, baseline update. Case study: 2026-06-05 GitHub cleanup |
| `references/cross-project-evaluation.md` | Decision tree for evaluating external projects before absorbing features (case studies: AnySearch, ECC, taste-skill) |
| `references/cross-project-evaluation.md` | Decision tree for evaluating external projects before absorbing features (case studies: AnySearch, ECC, taste-skill) |
| `references/absorption-analysis.md` | When to absorb external inspiration vs when NOT to (AnySearch case study) |
| `references/dual-role-patterns.md` | Two-pass cached review pattern: Advocate→Challenger→Synthesize, inspired by oh-my-hermes ralplan. Use during Step 3 audit or Step 9 deployment audit |
| `references/category-naming-pitfall.md` | Rule: don't create single-skill categories (note-taking/ case study) |
| `references/template-vs-command.md` | 🆕 Case study: descriptive labels vs imperative commands for agent compliance (claude-code 2026-05) |
| `references/cqi-plan-template.md` | 🆕 Template for CQI (持续质量改进) plan documents: dual-track structure (self-improvement + assist others), update log, issue log, success criteria |
| `references/cross-skill-defect-patterns.md` | 🆕 Cross-skill defect pattern library (P01-P16): recurring failure modes extracted from other skills' CQI plans. P13-P15 added from claude-code v4.1.0 optimization (MUST inflation, salience inversion, soft checklist). P16 added from claude-code v4.1.1 de-forking session (paper compliance/self-reported health). |
| `references/cross-phase-dependency-injection.md` | 🆕 P16: sub-agent inserting unbuilt P(N+1) deps into P(N) deliverables — morning-news-briefing 2026-06-03 case study |
| `references/research-backed-cqi-restructure.md` | Pattern for restructuring CQI plans with paper research, live infrastructure baselines, CC agent teams, and mechanical verification |
| `references/log-driven-cqi-mvp.md` | Log-driven Phase 1 CQI route: GitHub sync, per-skill changelog, read/modify/event checks, CQI/log separation, and Phase 2 deferral of cron/Kanban/A2A |
| `references/bundled-skill-drift-detection.md` | 🆕 Detecting locally-modified bundled skills: git show origin/main + sha256 comparison — catch version drift + stale residues |
| `references/bulk-text-replacement.md` | 🆕 Mass find-and-replace across many skill files: Python dict-driven pattern, multi-round strategy, YAML frontmatter gotchas |
| `references/skill-integrity-watchdog-recovery.md` | 🆕 Recovering skill-integrity-watchdog failures: recurrent profile-local shadows, stale runtime syncer, missing pool skill restoration, and cron verification |
| `references/runtime-grounded-cqi-audit.md` | Runtime-grounded CQI audit pattern: compare source vs deployed skill copy, score the artifact agents actually load, and treat same-version hash divergence as a high-severity event |
| `references/kanban-skill-cqi-phase2-pattern.md` | Kanban as Phase-2 execution layer for skill CQI: mode mapping, truth-source layering, runtime-grounded gates, MUSE-Autoskill lessons, and safe Phase-1.5 pilot |
| `references/structured-cqi-log-memory.md` | Structured CQI log-memory pattern: append-only JSONL truth source + manifest/provenance/schema writer, with SQLite/qmd/Kanban as derived indexes only. Use when revising Skill CQI logs or Kanban-driven quality workflows. |
| `references/skill-crystallization-roadmap.md` | 🆕 Skill 自动结晶路线：Obsidian 文档索引 + 四条路线概要 + 可运行系统（2026-06-05） |
| `references/muse-autoskill-insights.md` | 🆕 MUSE-Autoskill paper analysis (2026-06-04): per-skill memory, test gating, skill bank health — three actionable takeaways for Hermes skill system |
| `references/desensitization-audit.md` | 🆕 Comprehensive 28-pattern repo desensitization audit methodology — covers what sync-back.sh misses (vault names, personal names, cron IDs, app instance IDs, ports). Use before pushing skills to public repos. |
| `references/repo-import-profile-local-and-staged-audit.md` | Profile-local skill import + staged-only audit pattern for jz-skills pushes: copy from actual profile source, patch both sync directions, stage explicit paths, and whitelist VCS SSH remotes like `git@github.com`. |
| `references/skill-origin-classification.md` | 🆕 How to classify skills by origin (official vs self-made vs auto-generated): compare Hermes source repo, not `.bundled_manifest`. Case study: 2026-06-07 audit. |
| `references/agent-skillhub-context-map.md` | 🆕 Minimal context router for centralized SkillHub work: which config, ledger, audit, and Obsidian files to read by task. |
| `references/agent-skillhub-workflow.md` | 🆕 Centralized SkillHub workflows for creating, importing, modifying, exposing, and writing back skills without loading the full governance vault. |

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
- [ ] If this touched centralized SkillHub state, did I follow `references/agent-skillhub-context-map.md` and avoid reading the full Obsidian project unless required?
- [ ] If multi-profile: are Deployment & Sync rules embedded?

**Every box must honestly pass before deploying. If unchecked, fix it.**

---

> 📋 Changelog: `references/changelog.md`
> 🔄 Deployment & Sync: `references/deployment.md`
