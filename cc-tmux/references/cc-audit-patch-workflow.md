# CC Audit → Patch Workflow Pattern

> **Session source**: WRR full-project audit, 2026-06-28
> **Pattern**: Read-only audit first → discuss findings → graduated write permissions → multi-turn patch confirmation

---

## 1. When to Use

Complex tasks where **audit and fix are both needed**, but user wants control over what gets changed:
- Skill/project full audit
- Code review with fixes
- Documentation alignment audit
- CQI (Continuous Quality Improvement) document updates

**Not for**: simple mechanical fixes, emergency patches, or tasks where user already said "just fix it."

---

## 2. Workflow Steps

### Phase 1: Read-Only Audit (只读审核)

```
Hermes writes audit context → cc-send → CC reads + analyzes
  → CC produces: findings list with severity (blocker/high/medium/low)
  → CC produces: evidence per finding (file:line references)
  → CC produces: proposed fix for each (but does NOT apply)
```

**Key constraints on CC:**
- **Explicitly forbidden**: write files, edit code, run commands that modify state
- **Required**: every finding must cite `file:line` evidence
- **Required**: classify each finding by severity

**Context template** (add to cc-send context):
```markdown
## Audit Constraints
- This is READ-ONLY audit. Do NOT modify any files.
- Every finding must include: severity + file:line evidence + proposed fix (for discussion)
- Severity: BLOCKER (must fix) / HIGH (should fix) / MEDIUM (nice to have) / LOW (document only)
```

---

### Phase 2: Discuss Findings (讨论定级)

```
Hermes reads CC audit report → presents to user with 📡 block
  → User confirms/challenges severity classifications
  → User decides: "fix all HIGH+" or "only fix H1/H3" or "document only"
  → Hermes records decision as "audit scope confirmation"
```

**Common decision patterns:**
- "Fix all BLOCKER/HIGH, document MEDIUM/LOW"
- "Fix only specific items (H1, H3, M1)"
- "Some items are planned/expected — downgrade to LOW or mark as '计划内豁免'"

**Important**: When user says an issue is "planned but not done yet" (计划内豁免), CC must:
- Reclassify severity to LOW or exempt
- Document in CQI with status "planned / phase N"
- Not treat as "found a bug" but as "known gap, tracked"

---

### Phase 3: Graduated Write Permissions (分级写权限)

After user confirms scope, send CC a **new context** with explicit write authorization:

```markdown
## Approved Fixes (from audit discussion)
You are now authorized to apply the following fixes:
- [ ] H1: web_fetch provider contract alignment
- [ ] H3: query URL encoding
- [ ] M1: SearXNG engines固化

## Constraints
- Apply ONLY the approved fixes above
- After each fix: run verification (syntax check / smoke test)
- Do NOT fix unapproved items
- Produce diff summary after each fix for Hermes review
```

**Critical**: Never give CC blanket "fix everything" permission. Each patch must be:
1. **Proposed** (CC describes what it will change)
2. **Confirmed** (Hermes/user says yes)
3. **Applied** (CC makes the change)
4. **Verified** (CC runs tests/checks)

---

### Phase 4: Multi-Turn Patch Confirmation (多轮补丁确认)

For each approved fix:

```
Turn N:   CC proposes patch → "I will change X to Y. Confirm?"
Turn N+1: Hermes confirms → "Apply H1 fix"
Turn N+2: CC applies + verifies → "Applied. Syntax check passed."
Turn N+3: Hermes verifies (disk check) → "Confirmed on disk. Next: H3?"
```

**Why multi-turn instead of batch:**
- User may change mind after seeing first patch
- Early patch may reveal dependency on later patches
- Verification may fail, requiring retry
- User may want to adjust scope mid-way

**When to batch**: Only if all patches are independent, low-risk, and user explicitly said "apply all approved fixes at once."

---

## 3. Pitfalls from WRR Session

### Pitfall A: Looping on Same Query
When testing fixes, **do not repeat the same tool call expecting different results**. If `web_search` returns the same result 4 times with `idempotent_no_progress_warning`, stop and analyze logs instead of looping.

**Fix**: After 2 identical results, switch strategy: check logs, change parameters, or ask user.

### Pitfall B: Assuming "Plan内豁免" = "Not a Problem"
When CC finds an issue that is actually planned (e.g., OMP compatibility not yet implemented), the correct handling is:
- **Not**: "This is fine, ignore it"
- **Yes**: "This is a known gap, tracked in Phase 2, severity downgraded to LOW"
- Document in CQI with status: `⏸️ 计划内 — Phase N`

### Pitfall C: CC Self-Reporting as Evidence
CC may say "I verified this works" but that is **not sufficient evidence**. Always verify:
- Disk check: `ls -la /path/to/file` + `md5` / `wc -c`
- Syntax check: `python -m py_compile` / `tsc --noEmit`
- End-to-end: actual tool call with real parameters

**Rule**: CC's "I checked" = hint, not proof. Hermes must independently verify.

---

## 4. Verification Checklist (Post-Audit)

After all patches applied:

- [ ] Each approved fix has corresponding disk change (verified by Hermes)
- [ ] No unapproved changes were made (check `git diff` / `find -newer`)
- [ ] Syntax/lint checks pass for modified files
- [ ] Smoke tests run (if available)
- [ ] CQI document updated to reflect: fixed items → ✅, planned items → ⏸️ Phase N
- [ ] Version numbers bumped if behavior changed

---

## 5. Related Patterns

- **R2.1 Clarification Protocol**: `references/r2.1-clarification-protocol.md` — for complex task understanding before execution
- **Delegate Task Checkpoint Monitoring**: `references/delegate-task-checkpoint-monitoring.md` — for long-running CC tasks
- **Codex Planning Before CC**: `references/codex-planning-before-cc.md` — when planning and execution should be separated
