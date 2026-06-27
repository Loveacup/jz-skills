# Kanban as Phase-2 execution layer for Skill CQI

Use this reference when designing or revising a skill/CQI plan and the proposal involves Hermes Kanban, swarm, goal mode, or task boards for skill lifecycle management.

## Core decision

Kanban is viable for skill lifecycle CQI **only as a Phase-2 execution orchestration layer**. It should not enter the Phase-1 critical path and should never own skill truth, failure classification, acceptance decisions, or direct SKILL.md rewrites.

Phase 1 remains:
- read/modify/event hooks
- append-only issue/evolution logs
- per-skill changelog/provenance
- CC/manual CQI plan writing
- fresh-agent audit
- soft gates only

Kanban belongs after the log/manual/fresh-audit loop is stable.

## Boundary: what Kanban may and may not do

Kanban MAY:
- create read-only audit cards for a skill
- orchestrate a multi-step DAG: audit → classify → propose diff → fresh verify → human approve → deploy sync
- preserve task execution trace via runs/logs/events
- schedule or coordinate deployment sync after a change is already approved
- run fleet scans in Phase 2 when gateway/profile cost is acceptable

Kanban MUST NOT:
- be the source of truth for skill evolution history
- replace issue-log/evolution-log/changelog/provenance
- decide DISCOVERY / OPTIMIZATION / SKILL DEFECT / EXECUTION LAPSE by itself
- accept/reject a skill change by card status alone
- directly edit SKILL.md or references as an autonomous dispatcher action
- use goal-mode self-judging as a substitute for held-out/fresh-agent validation

## Recommended mode mapping

- **Single-task mode**: first Phase-2 pilot. One card = read-only fresh audit of one skill; output is a report artifact only.
- **Orchestrator mode**: mature default for complete CQI loops. Use `parents=[...]` so verify cannot start before proposal/audit artifacts exist.
- **Swarm mode**: only for night/fleet scans with explicit token, gateway, and profile-cost gates. It is not the default.
- **Triage mode**: draft a task graph from a vague CQI issue; do not auto-dispatch edit cards until a human/fresh auditor reviews the graph.
- **Goal mode**: avoid for skill body edits. Its judge is not a held-out validation gate. Acceptable only for non-edit aggregation/reporting work.

## Cron + Goal mode long-term rotation pattern

For sustainable quality improvement, use Cron only as a wake-up mechanism and Kanban only as the execution/control plane:

1. **Cron tick** creates or refreshes a CQI review cycle on a fixed cadence (weekly/biweekly/monthly) with a bounded scope: one skill family, one defect class, or one health-check query.
2. **Kanban Goal mode** may run long-lived non-edit work: aggregate logs, cluster repeated failures, identify stale/overlapping skills, prepare proposal bundles, and write review reports.
3. **Orchestrator mode** handles any actual change workflow after a proposal exists: audit → classify → proposal → fresh verify → human approve → apply → runtime/source hash verify → changelog/provenance update.
4. **No autonomous body edits**: worker output must stop at report/proposal/diff until a fresh verifier and human/explicit gate approves. Goal-mode `done` is not an approval signal.
5. **Cadence guard**: default to quiet operation; surface only completed report paths, blocked/high-risk findings, or required approvals. Avoid per-card status spam.

This makes the system sustainable: Cron supplies regularity, Kanban supplies traceability, and fresh verification/human approval prevents self-reinforcing skill drift.

## Truth-source layering

Keep three planes separate:

1. **Machine truth**: git/jsonl/changelog/provenance (`issue-log.jsonl`, `evolution-log.jsonl`, per-skill CHANGELOG, repo/ref/tree SHA/pin).
2. **Human board**: Obsidian CQI plans and summaries referencing issue IDs.
3. **Execution trace**: Kanban tasks/runs/logs/events referencing issue IDs.

Do not copy raw logs into Kanban comments as the canonical record. Do not treat `done` as proof that the skill improved.

## Runtime-grounded gate

Before any Kanban-driven audit or deploy step declares success, compare the runtime skill copy against the source/canonical copy:

```bash
wc -l "$SRC/SKILL.md" "$RUNTIME/SKILL.md"
md5 "$SRC/SKILL.md" "$RUNTIME/SKILL.md"   # macOS; md5sum on Linux
diff -q "$SRC/SKILL.md" "$RUNTIME/SKILL.md" || true
grep -n '^version:' "$SRC/SKILL.md" "$RUNTIME/SKILL.md"
```

Same version with different hash/content is a high-severity CQI event. Fix divergence before scoring.

## MUSE-Autoskill lessons to absorb cautiously

MUSE-style lifecycle framing is useful:
- skill creation
- skill-level memory
- management/merge/prune
- evaluation/tests
- refinement from runtime failures

For Hermes, absorb this as:
- per-skill `references/memory.md` or equivalent trial before adopting hidden `.memory.md`
- minimal trigger/invocation/regression tests for new or heavily revised skills
- skill-bank health checks for overlap, long-unused skills, and repeated failure clusters

Do not copy the whole runtime-auto-create pattern into Hermes Phase 1. A single successful trajectory can overfit accidental conditions; tests must include negative/regression cases, not just happy paths.

## Safe Phase-1.5 pilot

If the user wants an early Kanban experiment, constrain it to one read-only audit card:

- one skill under test
- one auditor assignee that actually exists/runs
- no SKILL.md writes
- output = report path + issue IDs
- card completion does not imply accepted skill change

Skip Phase 1.5 if it risks creating a second board of truth beside Obsidian and jsonl.
