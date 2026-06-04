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
