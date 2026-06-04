
## P16 — Cross-Phase Dependency Injection (by Sub-Agent)

**Classification:** 🐛 SKILL DEFECT

**Clinical presentation:** A sub-agent (CC) is assigned Phase N work. During execution, it modifies Phase N deliverables to include dependencies that belong to Phase N+1 — APIs, tools, or sources that haven't been built, tested, or validated yet. The injection is subtle: it reads as a natural "improvement" rather than a violation. Example: during P1a (search chain alignment), CC inserted `aihot API` as Lane C's primary discovery source — but aihot integration was P2 scope, with zero testing, no `aihot-source.md` reference, and no pre-flight check infrastructure.

**Root cause:** Sub-agents have no phase-boundary awareness. They optimize locally — "this search chain would be better with aihot" — without checking whether aihot is built, tested, or even within the current phase's scope. The reviewing agent (Hermes) must catch this, but may not if changes come as part of a large batch.

**Detection signals:**
1. A sub-agent's diff introduces references to tools/APIs/sources not mentioned in the phase plan
2. New `references/<name>.md` files are referenced but don't exist (`aihot-source.md` 404)
3. The sub-agent's own degradation table admits the dependency is unreliable ("无 SLA", "curl pre-flight 失败" → 回退)
4. The skill-authoring cross-skill-defect-patterns already has a case study about the same dependency never being deployed

**Fix:**
1. **Phase boundary gate:** Before accepting any sub-agent changes that touch routing tables or tool registries, verify every new dependency against the phase plan. If it's not in scope → revert or demote to stub.
2. **Pre-flight test before promotion:** Any dependency promoted to "primary source" must have a passing pre-flight test in the current environment. No test → stay auxiliary.
3. **Degradation table as signal:** If the sub-agent's own degradation strategy says "X 不可达 → 回退 Y+Z", X shouldn't be a primary source. Read degradation tables as self-incriminating evidence.
4. **Stale reference check:** `ls` the referenced file. If it's a 404, the dependency doesn't exist and the change is aspirational, not operational.

**Case study:** morning-news-briefing P1a → P2 boundary violation (2026-06-02/03)
- CC was assigned P1a (align search chain to WRR v3.9)
- CC inserted aihot as Lane C primary source (11 locations across SKILL.md + search-workflow.md)
- aihot was P2 scope, never tested, no integration code, no aihot-source.md
- User caught it: "aihot真的要当主源吗，你们测试过吗"
- Fix: 11 patches to demote aihot from "主源" to "仅兜底辅助", added pre-flight requirement, marked "无 SLA，未测试"

**Related patterns:**
- P10 (Assumed Integration from Design Doc): design doc ≠ deployed. P16 extends this to: sub-agent changes ≠ validated.
- P08 (Execution Lapse Misdiagnosis): this one was caught before it became a latent defect — the user's correction prevented it from hardening into skill content.
