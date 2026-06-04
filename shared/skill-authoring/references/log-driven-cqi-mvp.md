# Log-driven CQI MVP for Skill Evolution

Use this reference when a skill/CQI plan is being designed or revised and the scope risks jumping too early to cron, Kanban, A2A, or fleet-style inspection.

## Core decision

Phase 1 CQI should be **log-driven, CC-mediated, and manually gated**:

1. **Automated logging** captures read/modify/event signals.
2. **CC manually invokes the CQI Plan Writer** to consolidate logs into a CQI plan.
3. **Fresh CC/subagent audit** reviews the CQI output and proposed skill changes.
4. **Results are written back** to issue logs, evolution logs, and the skill changelog.

Hard boundary: automation records and reminds; CC/human judgment writes plans, audits, and approves skill edits.

## Phase 1 scope

Do:
- Use GitHub as the skill content source of truth when available.
- Track provenance in skill metadata or sidecar records: repo, ref, tree SHA, pin status.
- Keep append-only machine logs for observations and edits.
- Keep human-readable CQI plans in Markdown/Obsidian that reference issue IDs.
- Require every skill change to update that skill's changelog.
- Run quality gates after modification: frontmatter, description triggers/do-not, line budget/progressive disclosure, checklist, P01+ defect scan.

Do **not** put these in Phase 1's critical path:
- cron jobs
- Kanban orchestration
- A2A profile swarms
- continuous/fleet inspection
- autonomous skill rewriting

Those are Phase 2 after the log/manual/fresh-audit loop is stable.

## Three inspection cadences

### 1. Every read

Read hooks or skill load wrappers should check and surface:
- changelog summary: what changed recently
- provenance: source repo/ref/SHA/pin
- stale status: local differs from upstream tree SHA
- pending CQI/issues: open items that affect this skill

This is a read-only check. It may prompt or annotate; it should not rewrite the skill.

### 2. Every modify

Post-modify handling should append:
- `CHANGELOG.md` entry for humans
- `evolution-log.jsonl` event for machines
- quality gate verdict and any failed checks

MVP gate should warn or fail softly unless the user explicitly asks for enforcement.

### 3. Event-driven

Events that should create Issue Log entries:
- user correction ("not like this", "wrong order", "don't do X")
- explicit rule-correction instruction ("以后不要这样", "顺序错了", "补充这条规则", "记住这个流程") — record the original wording as a first-class signal, not just a vague summary
- tool/runtime error relevant to skill behavior
- audit finding from fresh CC/subagent
- repeated execution lapse or missing trigger

For correction-instruction events, preserve:
- `source_event_id` or transcript/message pointer
- original correction text
- affected skill or workflow class
- resulting changelog / CQI issue ID

Enough issue entries can then be consolidated into a CQI plan by the CQI Plan Writer.

## CQI and logs: integrate flow, separate storage

Recommended architecture: **integrated workflow, separated artifacts**.

- Logs: append-only, machine-readable, one event per line, referenced by ID.
- CQI plans: human-readable Markdown with problem map, traceability, gates, measurement gap, and timeline.
- Join key: `ISSUE-<SYSTEM>-<NNN>` or equivalent stable issue ID.

Do not merge raw logs into CQI Markdown. Do not use Markdown plans as the only event log.

## Web research as consultation

Skill-authoring may call `web-research-router` during CQI design, but only as a consultative branch, not as a default hook.

Trigger external research only when one of these holds:
- a defect pattern repeats 3+ times and local evidence has no fix
- references or claims appear stale/rotted
- local evidence conflicts and needs external adjudication
- the plan needs to absorb new papers/projects/methods

Output should be an external evidence card:
- claim/problem
- 2-4 source-backed findings
- applicability: confirmed vs inferred
- recommendation: concrete rule/change target

Cost controls:
- local-first search before web
- at most one web research pass per CQI consolidation
- cache by query hash/date for ~30 days
- batch related claims
- degrade to `pending-research` if budget is exceeded

## Patch guidance for CQI plan documents

When revising an existing CQI plan:
- Reframe existing cron/Kanban/A2A/inspection material as Phase 2, not deleted.
- Rewrite Phase 1 MVP around GitHub sync, read/modify/event hooks, append-only logs, CQI Plan Writer, and fresh-audit.
- Add an explicit responsibility boundary: CQI Plan Writer writes plans and audit handoffs; it does not edit or approve skills.
- Add audit handoff output: skill under test, evidence inputs, proposed gates, invocation checks, expected writebacks.
