# Cross-Skill Defect Pattern Library

> Extracted from Hermes skill CQI plans, issue logs, and deployment audits. Each pattern is a recurring failure mode observed across multiple skills. When auditing a skill, check against this library.

## P01 — Template as Command Confusion

**Classification:** 🐛 SKILL DEFECT

**Clinical presentation:** Section headers like 「汇报模板：」「示例：」「参考格式：」are read by agents as reference material, not mandatory instructions. Agent rationalizes: "this is just an example, I can adapt it."

**Root cause:** Non-imperative labels. Agents interpret section headers literally — descriptive labels mean "this is for reference," imperative labels mean "this must be followed."

**Fix:** (1) Rewrite label as imperative: 「必须严格按此格式，不按模板 = 未完成」; (2) Add Execution Lapse pre-interception blockquote; (3) Bind format requirement to a Core Rule.

**Source skills:** claude-code (2026-05), multiple others

**Case study:** `skill-authoring/references/template-vs-command.md`

---

## P02 — Sync Script Fracture

**Classification:** 🐛 SKILL DEFECT

**Clinical presentation:** `sync-all.sh` is updated with new skill paths, but `sync-back.sh` is forgotten. Result: forward sync works, reverse sync silently broken.

**Root cause:** Dual-script maintenance burden. Two scripts must stay in sync but no automated check enforces this.

**Fix:** (1) After any sync script edit, verify both; (2) Dry-run test both directions; (3) Consider consolidating to single bidirectional script.

**Source skills:** Multiple (governance infra, 2026-05)

---

## P03 — Reference Rot

**Classification:** 🔍 DISCOVERY

**Clinical presentation:** A skill's `references/` section points to files that have been deleted, renamed, or moved. Agent loads skill → attempts to access reference → gets 404/file-not-found → proceeds without critical context.

**Root cause:** No automated reference integrity check. When skills are restructured or consolidated, stale reference pointers are not cleaned up globally.

**Fix:** After any consolidation/deletion: `grep -rn "<old-name>" ~/.hermes/skills/ --include="*.md"` and fix ALL matches. Also check jz-skills repo.

**Source skills:** web-research-router, grill-with-docs, skill-authoring (github-code-explorer → github consolidation, 2026-05)

---

## P04 — Silent-Bypass

**Classification:** 🔍 DISCOVERY

**Clinical presentation:** A skill's SKILL.md is valid and well-structured, but when deployed to a fresh agent, the agent never invokes it. The skill is loaded (visible in available_skills) but the agent rationalizes: "I can handle this without loading that."

**Root cause:** (1) Description not pushy enough — trigger phrases too generic; (2) Skill name not salient in the task context; (3) Agent overconfidence in its own ability to handle the task.

**Fix:** (1) Strengthen description with explicit trigger phrases; (2) Add "load this skill FIRST" in Red Flags; (3) Test with fresh agent (different model) before shipping.

**Source:** SkillEvolver paper (2026-05), confirmed in multiple Hermes skills

---

## P05 — Multi-Profile Name Ambiguity

**Classification:** 🐛 SKILL DEFECT

**Clinical presentation:** `skill_view("skill-name")` returns `Ambiguous skill name: 2 skills match...` when a profile uses `external_dirs` to share skills from another profile. Both copies are found and the tool refuses to guess.

**Root cause:** Hermes profiles sharing skills via `external_dirs` creates duplicate paths. The `skill_view()` resolver finds both and errors instead of picking one.

**Workaround:** (1) Use `read_file` with absolute path instead of `skill_view`; (2) Pass `cross_profile=True` for `skill_manage`; (3) Use `terminal` for bulk writes to bypass the guard.

**Root fix candidate:** Categorized path resolution — pass `category/skill-name` format to disambiguate.

**Source skills:** All skills used by cron-worker profile (2026-05-31+)

---

## P06 — Progressive Disclosure Drift

**Classification:** ⚡ OPTIMIZATION

**Clinical presentation:** A SKILL.md starts at <300 lines but incremental additions push it past the threshold without anyone noticing. Content that should be in `references/` accumulates in the main body.

**Root cause:** No automated line-count check. Each edit adds 5-10 lines; after 20 edits, the file is silently oversized.

**Fix:** (1) `wc -l SKILL.md` after every patch; (2) If >300, move least-critical sections to `references/`; (3) Consider a pre-commit hook.

**Source skills:** Multiple (ongoing)

---

## P07 — Patch Fuzzy-Match Corruption

**Classification:** 🐛 SKILL DEFECT

**Clinical presentation:** A `patch` operation with `old_string` that doesn't precisely match any line triggers fuzzy matching. The tool matches a NEAR-but-wrong section and replaces a MUCH larger block than intended — e.g., 188-line file → 54-line file because unrelated content was consumed.

**Root cause:** `patch` tool's fuzzy matching as fallback when exact match fails. Agent doesn't verify `wc -l` or spot-check after patching.

**Fix:** After ANY `patch`: (1) `wc -l` to verify file size; (2) Spot-check first line; (3) If file suddenly shorter, `cp` from known-good source and re-patch with exact strings from fresh read.

**Source skills:** mac-doctor cron-module.md (2026-05-31)

---

## P08 — Execution Lapse Misdiagnosis

**Classification:** 🏃 EXECUTION LAPSE — but frequently MISCLASSIFIED as 🐛 DEFECT

**Clinical presentation:** Agent fails to produce correct output. Reviewer examines the skill and finds the instructions are correct — but instead of classifying as "agent didn't follow," they change the skill rules themselves. Valid content is corrupted.

**Root cause:** Failure to run the EmbodiSkill classification FIRST before revising. Default human/agent instinct is "fix the rule" when "enforce the rule" is the right action.

**Fix:** (1) Before ANY revision, classify the failure: DISCOVERY / OPTIMIZATION / DEFECT / EXECUTION LAPSE; (2) If LAPSE — do NOT change skill body, add emphasis to appendix; (3) If DEFECT — only change the IMPLICATED rule, not whole skill.

**Source:** EmbodiSkill paper (2026-05), confirmed across multiple skill audits

---

## P09 — Premature Conclusion from Contradictory Evidence

**Classification:** 🐛 SKILL DEFECT

**Clinical presentation:** You test approach X on tool Y, it fails. You declare "Y doesn't work for X." Later, someone else succeeds with the same approach. Trust is burned because the conclusion was finalized without reconciling the contradiction.

**Root cause:** Single-source testing treated as definitive. When own experiment fails, the default conclusion is "tool doesn't work" rather than "my configuration might be wrong, let me investigate why others succeed."

**Fix:** When own test contradicts others' success: (1) Flag as contradiction, NOT conclusion; (2) Propose investigation steps (align config, compare environment, etc.); (3) Suspend conclusion until reconciled.

**Source:** Scrapling WeChat testing (2026-06-01)

---

## P10 — Assumed Integration from Design Doc

**Classification:** 🐛 SKILL DEFECT

**Clinical presentation:** You read a technical analysis document that describes an integration design in detail (API endpoints, curl templates, field mappings). You assume it's already live and reference it as fact. User corrects: it was a proposal/design, never implemented.

**Root cause:** Design documents and technical breakdowns describe WHAT COULD BE, not necessarily WHAT IS. Without an explicit "deployed? yes/no" field, the reader fills in the gap with assumption.

**Fix:** When referencing any design/proposal/analysis document, explicitly CHECK: "Is this already live, or is this a plan?" before treating it as current state.

**Source:** aihot + xhs-tech-writer design doc (2026-06-01)

---

## P11 — Replace Instead of Append on Plans

**Classification:** 🏃 EXECUTION LAPSE

**Clinical presentation:** User says "加到计划里" (add to the plan). Agent interprets this as "modify the plan" and uses `patch` to replace existing content with new content. The tool rejects it (old_string = new_string), revealing the intent mismatch.

**Root cause:** The words 加/追加/补充 (add/append/supplement) were interpreted as "modify" rather than "append." The agent defaulted to its usual `patch` workflow instead of the `append` workflow appropriate for document extension.

**Fix:** When user says 加/追加/补充/添加: (1) Read file to find insertion point; (2) Append AFTER the target section, don't replace; (3) If the entire section needs restructuring, ask first.

**Source:** WRR CQI plan Thread D append (2026-06-01)

---

## P12 — Over-Automated CQI MVP

**Classification:** ⚡ OPTIMIZATION

**Clinical presentation:** A CQI plan jumps straight to cron/Kanban/A2A/fleet inspection as Phase 1. But the intended MVP was simpler: log automation → CC-mediated CQI Plan Writer → fresh CC audit → writeback. The automation scaffolding is built before the core loop is stable.

**Root cause:** Automation bias — "if it's worth doing, it's worth automating immediately." Phase 1 should validate the log → manual → audit loop first. Only after the human judgment boundary is tested should automation be layered on.

**Fix:** (1) Phase 1: log-driven + manual gating (hooks + append-only jsonl + CC manual + fresh CC audit); (2) Phase 2: cron/Kanban/A2A/continuous inspection only after Phase 1 loop is stable; (3) Add a Phase 2 entry gate: "Phase 1 jsonl ≥ 50 entries with no systemic misclassification for 30 days" before unlocking automation.

**Source:** skill-authoring CQI plan (2026-06-01), claude-code CQI plan (2026-06-01)

**Case study:** `skill-authoring/references/log-driven-cqi-mvp.md`

---

## P13 — MUST Inflation

**Classification:** 🐛 SKILL DEFECT

**Clinical presentation:** SKILL.md contains 23+ MUST directives, but the user only truly cares about 3 of them (session cleanup, effort declaration, discussion protocol). The remaining 20 MUSTs are ignored by agents through "automation silence" — the agent still loads the skill but internally deprioritizes all MUSTs because the density creates a flat salience landscape. Every rule screams at the same volume, so none are heard.

**Root cause:** Incremental MUST accumulation. Each pitfall correction adds another MUST without auditing whether existing MUSTs are still enforced. Over time, MUSTs lose all meaning — they become wallpaper.

**Fix:** (1) Audit: list every MUST in the skill, ask "does the user actually care if this is violated?"; (2) Classify into tiers: 🔴 Red-Line (user cares, ≤3) / 🟡 High-Importance / 🔵 Reference; (3) Red-Lines get Constitutional placement (top 10% of file) + anti-rationalization micro-table; (4) Non-red-line rules use weaker framing (should/prefer) or move to references/.

**Source:** claude-code v4.1.0 optimization (2026-06-02): 23 MUSTs → 3 true red-lines, 588→524 lines

**Detection heuristic:** `grep -ci 'must\|必须\|MUST' SKILL.md`. If count > 5 on a <600-line skill, suspect MUST inflation. Cross-check with user: "which of these do you actually consider non-negotiable?"

---

## P14 — Salience Inversion

**Classification:** ⚡ OPTIMIZATION

**Clinical presentation:** Instructions that the user considers *critical* (reporting format, discussion protocol, safety constraints) are placed at the same visual/structural weight as minor instructions (effort estimation, reference pointers, formatting preferences). Because LLM attention follows a natural decay curve, late-placement critical rules are effectively invisible — the agent has already formed its action plan before reaching them.

**Root cause:** Content is organized by *topic* (all rules together) rather than by *salience* (critical first, optional last). The author knows which rules matter most but doesn't encode that knowledge structurally.

**Fix:** (1) Move user-critical rules to Constitutional block in top 10% of file; (2) Use structural grading: 🔴 Red-Line header → 🚦 Gate Stamp → 📡 Real-time obligations → reference material; (3) Never place a "must follow immediately" rule below line 100 of a 500-line file.

**Source:** claude-code v4.1.0 optimization (2026-06-02): 📡 reporting + discussion protocol moved from scattered locations to Constitutional header at :20-44

**Detection heuristic:** Identify the top-3 rules the user has complained about being skipped. If any of them are below line 100, salience inversion is present.

---

## P15 — Soft Checklist

**Classification:** 🐛 SKILL DEFECT

**Clinical presentation:** Section headers like 「汇报模板：」「格式参考：」「建议格式：」are read by agents as *suggestions*, not requirements. Even when the actual content following the header contains imperative language, the descriptive label overrides it — the agent rationalizes: "this section is labeled as a template, so I can adapt it."

**Root cause:** Labels set the compliance frame. A descriptive label ("Template:") signals "this is reference material." An imperative label signals "this must be followed." The label is read first and colors interpretation of everything that follows.

**Fix:** (1) Rewrite label as imperative: 「必须严格按此格式执行，不按模板 = 未完成任务」; (2) Add Execution Lapse pre-interception at top of section: "⚠️ This is NOT a reference example. You MUST follow this exact format."; (3) Bind format requirement to a Core Rule with gate-check.

**Relation to P01:** P01 (Template as Command Confusion) is the broader pattern — descriptive labels fail. P15 refines this with the specific mechanism: **the label, not the content, sets the compliance frame.** P15 is the root mechanism; P01 is the symptom.

**Source:** claude-code v4.1.0 optimization (2026-06-02): 「汇报模板：」replaced with 「📡 必须严格按此格式汇报（非模板、非参考）」

**Detection heuristic:** `grep -in '模板\|示例\|参考\|建议\|格式' SKILL.md`. For each match, ask: "is this mandatory or illustrative?" If mandatory, rewrite the label immediately.

---

## P16 — Paper Compliance / Self-Reported Health (纸面合规/自报健康)

**Classification:** 🐛 SKILL DEFECT

**Clinical presentation:** A CQI plan or skill document claims full health — all metrics ✅, all gate checks passing, all infrastructure "built." But upon empirical verification: (a) the cron job was never created; (b) the health-check script was never written; (c) the log files were never initialized; (d) the metrics were measured on the WRONG copy of the file (source repo, not the deployed version agents actually load); (e) the "three-endpoint sync" diagram shows paths that don't exist on disk. The entire compliance report is a paper construct.

**Root cause:** Self-reported health without empirical verification. The author writes what SHOULD exist and marks it as done, without ever checking whether it DOES exist. Trust in the plan replaces verification of the plan. This is recursive — the very CQI plan meant to prevent this class of error is itself infected (RA-13).

**Fix:** (1) Every health claim must cite a verifiable artifact: `wc -l` output, `md5 -q` hash, `ls` directory listing, cron `job_id`; (2) Measurements MUST be taken from the deployed/runtime copy, not the source repo — "测的就是跑的"; (3) "All ✅" is a red flag — healthy systems have WIP items and known issues; (4) Add a "诚实度自检" step that explicitly checks: "did I measure the right file? does this mechanism actually exist on disk? is this cron job in `hermes cron list`?"

**Source:** claude-code CQI plan v4.1.0 (2026-06-01/02): six-dimension scorecard claimed "全✅" while deployed SKILL.md was 647 lines with broken pitfall numbering, none of the Phase 1 infrastructure existed, and measurements were taken from source repo not deployed copy. Discovered via CC fresh audit (event #3).

**Detection heuristic:** (1) Grep for `✅` or `全✅` in CQI/health documents — each one should have a verifiable command output next to it; (2) `hermes cron list` to verify cron jobs actually exist; (3) `wc -l` + `md5 -q` on BOTH source and deployed copies to detect "测A跑B"; (4) `find` or `ls` to verify files referenced in plans actually exist on disk.

**Relation to P10:** P10 (Assumed Integration from Design Doc) is about assuming a design is live. P16 extends this to CQI: assuming your own improvement mechanisms are live because you wrote them down.
