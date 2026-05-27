# Tool-Call Risk Audit Pattern for regent / 三省六部

Use this reference when auditing the default agent, regent, profile toolsets, plugins, cron jobs, or multi-agent tool policy.

## Core finding pattern

The main governance risk is often not “too many tools” by itself; it is **high-side-effect tools exposed broadly while enforcement lives only in prompt/SOUL rules**. A治理 profile such as `regent` may need strong read/query ability, but should not hold unconstrained execution/control-plane authority by default.

## Audit sequence

1. Load `hermes-agent` first for Hermes/profile/tooling questions, then this constitution.
2. Inspect actual config for both default and target profile; never infer regent from default.
3. Resolve toolsets, especially umbrella toolsets such as `hermes-cli`, because they may include terminal, file writes, cron, messaging, memory, delegation, browser, skills, and kanban tools.
4. Check enabled plugins and pre-tool-call hooks; identify exactly which tools they intercept.
5. Check cron jobs and whether they are script-only/no-agent, agent-driven, recurring, high-frequency, or user-visible.
6. Check audit logs for denied operations and repeated failure modes, but do not treat old transient setup errors as durable rules.
7. Classify each tool as hard-gate / soft-prompt / allow-read-only.
8. Recommend hook/check_fn/profile-toolset changes over longer prompt text.

## Hard-gate candidates

Hard gates should apply to side-effect and persistence surfaces, especially when run by `regent` or scheduled jobs:

- `cronjob`: create/update/resume/run/remove, schedule changes, skill attachment, high-frequency visible jobs.
- `send_message`: explicit targets, group/DM sending, worker-originated direct delivery, cron delivery, acting as the user.
- `memory` / hindsight retain/remove: long-term memory writes, user profile writes, cross-profile memory changes.
- `terminal`, `write_file`, `patch`, `skill_manage`: control-plane files, destructive shell, profile/SOUL/plugin/config/cron/memory/provider changes.
- `delegate_task` and kanban dispatch: recursion depth, parent/task_id, budget, timeout, acceptance criteria, assignee.
- Kanban mutators: create/complete/block/unblock/link/archive/delegate/specify.

## Soft-prompt or low-friction candidates

Usually do not hard-confirm every use of:

- read/search/extract tools (`read_file`, `search_files`, `web_search`, `web_extract`, `session_search`).
- `skill_view`, `skills_list`.
- `kanban_show`, `kanban_list`, usually `kanban_comment` / `kanban_heartbeat` with rate discipline.
- `todo` and process polling/log/wait for processes the agent started.

Over-gating read-only tools reduces correctness and increases user burden.

## Regent-specific principle

Preserve default-agent strengths that improve reliability:

- tool-verified facts;
- “say-do” discipline;
-能查不问;
- verification before completion claims;
- cautious external side effects.

Do **not** import default-agent “do it all yourself” behavior into regent. Regent should govern, dispatch, audit, and synthesize; execution belongs to the relevant ministry/profile unless the task is genuinely simple and low risk.

## Red flags

- `regent` has a broad umbrella toolset such as `hermes-cli` with no disabled high-risk tools.
- SOUL says “do not execute” but profile still exposes terminal/patch/write_file/cron/send_message/memory without hard gates.
- A plugin only gates `kanban_*` while other high-side-effect tools remain ungated.
- State lookup failure defaults to allowing high-risk state transitions.
- Cron prompt scanning exists but cron creation/update is still unrestricted.
- Workers can send messages directly via task environment without target/rate/task binding checks.

## Recommendation shape

Prefer concrete controls in this order:

1. Profile-level toolset minimization.
2. pre-tool-call hooks/check_fn for high-risk tools.
3. Path/action/target/task-aware policy checks.
4. Audit logs for allowed and blocked side-effect operations.
5. Short prompt/SOUL reminders only for behavior that cannot be enforced mechanically.

Avoid adding more long constitutional prose when a hook or toolset split would enforce the rule more reliably.
