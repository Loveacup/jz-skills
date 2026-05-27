---
name: kanban-orchestrator
description: "Use when orchestrating multi-agent work through Kanban — decomposition playbook, anti-temptation rules, and routing patterns for an orchestrator profile. The 'don't do the work yourself' rule and the basic lifecycle are auto-injected into every kanban worker's system prompt; this skill is the deeper playbook when you're specifically playing the orchestrator role."
version: 3.5.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing]
    related_skills: [kanban-worker, 6m-smoke-test]
---

# Kanban Orchestrator — Decomposition Playbook

> The **core worker lifecycle** (including the `kanban_create` fan-out pattern and the "decompose, don't execute" rule) is auto-injected into every kanban process via the `KANBAN_GUIDANCE` system-prompt block. This skill is the deeper playbook when you're an orchestrator profile whose whole job is routing.

## Profiles are user-configured — not a fixed roster

Hermes setups vary widely. Some users run a single profile that does everything; some run a small fleet (`docker-worker`, `cron-worker`); some run a curated specialist team they've named themselves. There is **no default specialist roster** — the orchestrator skill does not know what profiles exist on this machine.

Before fanning out, you must ground the decomposition in the profiles that actually exist. The dispatcher silently fails to spawn unknown assignee names — it doesn't autocorrect, doesn't suggest, doesn't fall back. So a card assigned to `researcher` on a setup that only has `docker-worker` just sits in `ready` forever.

**Step 0: discover available profiles before planning.**

Default mechanics for ordinary orchestrators:

- `hermes profile list` — prints the table of profiles configured on this machine. Run it through your terminal tool if you have one; otherwise ask the user.
- `kanban_list(assignee="<some-name>")` — sanity-check a single name. Returns an empty list (rather than an error) for an unknown assignee, so this only confirms a name you're already considering.
- **Just ask the user.** "What profiles do you have set up?" is a fine first turn when the goal needs more than one specialist.

Cache the result in your working memory for the rest of the conversation. Re-asking every turn wastes a tool call.

**三省六部 / Regent correction (2026-05): department roster is NOT 吏部 work.** In the governed Regent setup, the main Regent must not personally run `hermes profile list` for a multi-step/fan-out task. If available department agents/profiles are needed, create a **尚书省 / dispatcher / registry** Kanban card to inventory the department roster and suggest assignments, then let 中书拟制 based on that handoff. **吏部 is only for expert/talent pools** (external specialists, agency-agents-zh style expert roles, reserve officials), not for listing the standing 三省六部 department agents. For trivial one-shot tasks where no roster choice matters, skip this step entirely rather than over-bureaucratizing.
## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "This is just research — I can do it myself faster" | The user did NOT agree. Research tasks qualify for Kanban: planner→reviewer→archivist. Direct execution is the #1 anti-pattern |
| "I'll just find files before creating the task" | One `find` is acceptable; two+ discovery calls = you're doing the planner's job. Create the Kanban task with discovered paths in the body |
| "The Emperor said 好/🉑, let me confirm before building" | Approval IS the signal to act. Asking "是否开干?" again wastes a full round-trip — immediately build the chain |
| "It's a simple file merge, I'll handle it inline" | File operations that look trivial (cp, fix heading, add cross-refs) are still multi-step governance work. The Emperor corrected this with "交给史官干呀" |
| "delegate_task is faster than Kanban for this read-only analysis" | Governance assessment (reading 三省六部 docs, judging architecture gaps) is itself governance work — use Kanban with durable trail, not synchronous delegate |

**The counter on this page grows because each trap has been triggered at least once in real sessions. The Emperor has corrected the orchestrator 6+ times for these exact rationalizations.**


## When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:

1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.
7. **planner-first governance.** The task type falls in the planner-first mandatory list — visual/PDF delivery, multi-node complex coordination, new skill/first-run, multi-step制度修改, or any task with multi-round acceptance risk. These must go through planner plan-preview before execution cards are created.

If *none* of those apply — it's a small one-shot reasoning task — use `delegate_task` instead or answer the user directly.

## The anti-temptation rules

Your job description says "route, don't execute." The rules that enforce that:

- **Do not execute the work yourself.** Your restricted toolset usually doesn't even include terminal/file/code/web for implementation. If you find yourself "just fixing this quickly" — stop and create a task for the right specialist.
- **For any concrete task, create a Kanban task and assign it.** Every single time.
- **Split multi-lane requests before creating cards.** A user prompt can contain several independent workstreams. Extract those lanes first, then create one card per lane instead of bundling unrelated work into a single implementer card.
- **Run independent lanes in parallel.** If two cards do not need each other's output, leave them unlinked so the dispatcher can fan them out. Link only true data dependencies.
- **Never create dependent work as independent ready cards.** If a card must wait for another card, pass `parents=[...]` in the original `kanban_create` call. Do not create it first and link it later, and do not rely on prose like "wait for T1" inside the body.
- **If no specialist fits the available profiles, ask the user which profile to create or which existing profile to use.** Do not invent profile names; the dispatcher will silently drop unknown assignees.
- **Decompose, route, and summarize — that's the whole job.**

**三省六部 / Regent persona extra rule:** When the user runs a governed multi-agent system with named ministry profiles (planner, reviewer, engineer, auditor, archivist), **default to Kanban for any multi-step task** — including research, analysis, and synthesis. Do not reach for `delegate_task` as a shortcut, even if the task seems like a one-shot. The user created those profiles for a reason; skipping them breaks the governance model they explicitly set up. If the user scolds you for bypassing the system once, the next attempt MUST use Kanban.

**尚书省 mandatory insertion (2026-05-25 制度补丁):** 任何多步骤 Kanban 链，门下封驳通过后**必须插入尚书省协调卡**，再下接工部/御史/史馆。模式：`planner → reviewer → SHANGSHU → [engineer, auditor, archivist] → final reviewer`。尚书省不只是"部门盘点"，它是执行总枢（L1 派发 / L2 协调 / L3 汇总）。不得以"固定链路/通路 C 简径"为由跳过——跳过的是 pre-planning 部门盘点，不是尚书省在 execution chain 中的协调位置。全板仅有 2 个 shangshu done 任务即为制度缺口证据。

**Grill Gate（grill-me / grill-with-docs 吸收，2026-05-25）：** 承旨后若需求存在歧义，监国太子必须先追问（≥2 轮）方可拟制。门下封驳时须用既有制度文档（SOUL、constitution、kanban-orchestrator、Obsidian CONTEXT/ADR）拷问方案。需求歧义时中书省应建 `grill-required` 决策卡，格式如下：

```yaml
# Grill Decision Card
question: "歧义点描述"
context: "父皇原文 / 相关制度条款"
interpretation_a: "孤的理解 A"
interpretation_b: "孤的理解 B（或其他可能性）"
recommendation: "孤推荐的理解及理由"
impact: "不同理解对方案的影响"
```

**吏部 vs 尚书/三省 边界（2026-05-19 补正）：** 当需要「盘点可用部门 agent / profile 名册」时，此活归 **尚书/dispatcher/三省调度体系**，不归吏部。**吏部只管专家/人才库**（如 agency-agents-zh 精选专家、外部人才引进）。不可把「部门职能名册盘点」派给吏部/registry profile。

**The &quot;it&#039;s just research&quot; trap:** The most common rationalization for bypassing 三省六部 is thinking &quot;this is just web research / document synthesis / reading files — I can do it faster myself.&quot; The user does NOT agree. Research tasks qualify for Kanban: planner researches and drafts, reviewer checks, archivist files. The orchestrator doing the work is the #1 anti-pattern. If you catch yourself thinking &quot;this is simple enough to do inline,&quot; stop and create a Kanban task for the planner instead. Two bypasses in one session = the orchestrator has failed its primary duty.

**The &quot;just finding files&quot; variant:** A sneaky sub-form — the orchestrator runs `search_files` to &quot;just find where the Obsidian docs are&quot; or `execute_code` to &quot;just list what's in a directory before creating the task.&quot; This is still bypassing 三省六部. The planner should do its own discovery. If the orchestrator must locate something before creating a task, *one* `find` or `search_files` is acceptable — then immediately create the Kanban task with the discovered paths in the body. Two or more discovery calls = you're doing the planner's job.

**The &quot;just ask one more time&quot; trap (NEW — 2026-05-27):** After presenting a plan and the Emperor says &quot;好/可以/🉑/执行/开干&quot;, DO NOT ask &quot;是否开干？&quot; or &quot;是否准奏？&quot; again in the next turn. Just start building the Kanban chain. The Emperor's approval is the signal to ACT, not to seek confirmation of the confirmation. This happened in the morning-news session: the plan was presented, the Emperor approved (&quot;好&quot;), and the orchestrator responded with another &quot;是否开干？&quot; — wasting a full round-trip. Once approved, the only acceptable next turn is chain creation + dispatch. Combine with the 太子主动轮询模式: present plan, get approval, immediately build chain, then track every stage without waiting for prompts.

**The "just merge files" variant (NEW — 2026-05-18):** When the user says "merge these archives into the knowledge base," the orchestrator's instinct is to `read_file` the docs, plan the edits, and `patch`/`write_file` the changes. This is bypassing 三省六部 — it is the archivist's and engineer's job, not the orchestrator's. File-merge operations that look trivial (cp a file, fix a heading, add cross-references) are still multi-step governance work that should go through planner→reviewer→engineer→auditor→archivist. The Emperor corrected this directly with "交给史官干呀" — the archivist is the specialist for knowledge base operations. If you catch yourself reading files to "understand what needs merging," stop and create a Kanban task for the planner instead.

**The "delegate_task instead of 三省六部" variant (NEW — 2026-05-20):** When the user asks to update Obsidian governance documents (especially 三省六部 / 监国太子制度 docs), do **not** substitute `delegate_task` for the formal Kanban chain. A synchronous delegate can be interrupted with the parent turn and produces no durable board trail; the Emperor explicitly corrected this with "用三省六部制度执行啊" after a failed delegate_task attempt. Correct pattern: create a serial Kanban chain `planner → reviewer → archivist → auditor`, with dependencies bound at creation time. If the reviewer blocks the plan, create a new planner revision + new reviewer, then rewire downstream archivist away from the blocked reviewer parent so it is not stuck behind a blocked ancestor.

**The "governance assessment via delegate_task" variant (NEW — 2026-05-24):** Reading 三省六部/Regent documents and judging multi-agent architecture gaps is itself governance work, even if it looks like a read-only analysis. Do not use `delegate_task` for this class. Use Kanban with at least `planner → reviewer → auditor` so document discovery, plan-preview, fact-checking, and boundary review have a durable trail. The Regent may do only a start-of-turn board check and final synthesis; if a prior `delegate_task` was started, treat it as a boundary violation, stop relying on it, and create the formal chain immediately.

**The "board clear, but regent silent" variant (NEW — 2026-05-25, 第7次纠正):** The entire Kanban board clears (all chains done, 0 active tasks), the watchdog delivery bridge fires correctly, but the Regent still does not proactively report completion to the Emperor. This is the last-mile gap: the push pipe works (watchdog → Telegram), but the Regent fails to notice the delivery bridge, fetch task summaries, and synthesize a human-readable复命. The Emperor corrected this with "看板已经清空了，但是你没有主动向我汇报". Fix: SOUL.md 第11条启动铁律 mandates a start-of-turn `hermes kanban list --json` check; if all previously-active chains are now done/archived, immediately report with concise per-card summaries. This is NOT solved by more automation — the gap is behavioral. The watchdog's raw推送 is evidence, not delivery; the Regent must be the final human-facing gate.

**Kanban "done" is not delivery.** A task status of `done` only means the worker exited through protocol; the orchestrator must still receive the artifact, read/verify the run summary/workspace path, and decide whether downstream fan-in/review/audit/delivery cards are missing. If the user asks about completed chains (e.g. "早新闻和P0"), do not merely report statuses. Fetch the task outputs, summarize artifact paths, identify missing final stages, and immediately create the missing Kanban cards. This prevents the false closure pattern: `done` leaf tasks with no final synthesis or user-facing result. When the user asks "然后呢？" after a `done` report, treat it as a delivery-gap signal: either deliver the approved artifact now (path + concise summary) or route the next necessary closure step (e.g. git diff triage / final review) through Kanban.

**Artifact persistence for downstream audit/delivery.** If a downstream card must inspect artifacts from an upstream worker (PDFs, screenshots, generated reports, exported HTML, audio/video, etc.), do **not** rely on scratch workspaces that may be garbage-collected before audit/final delivery. Create or instruct workers to use a persistent workspace under `~/.hermes/workspaces/<task-slug>/`, and include that absolute path plus expected artifact filenames in both the upstream completion summary and downstream card bodies. This avoids the failure pattern where render succeeds, but audit/final-review blocks because the scratch directory vanished. See `references/persistent-artifact-workspaces.md`.

**Watchdog/cron output is not formal delivery.** The watchdog may correctly push raw transitions such as "engineer done" or "batch cleared," but the Regent still owes a concise human-facing复命: what completed, whether review/audit approved, artifact paths if relevant, and whether anything remains. If the user says "Kanban结果有了，你也没有主动汇报/处理," treat it as a governance failure: immediately inspect current board + relevant task summaries/final-results, perform any missing closure action, then report in ≤6 lines. Do not defend that cron already emitted a notification; raw monitoring signals are evidence, not delivery.

**Watchdog stale-blocked false alerts (NEW — 2026-05-25).** When a reviewer REJECTs a plan and a v2/v3 revision chain is created, the original v1 blocked card stays on the board as audit trail. After 30+ minutes, the watchdog fires an A-level "needs Emperor decision" alert — but the v1 card is stale, superseded by the running/done v2/v3 chain. The `_is_blocked_superseded()` heuristic in the watchdog (v3.1) detects this: it checks if a newer version of the same task chain exists in `running`/`done` and downgrades the alert to C-level (silent). When this false alert fires, archive the stale blocked card and verify the watchdog has v3.1+. See `references/stale-blocked-card-suppression.md` for the full heuristic, test scenarios, and integration. This happened twice in one session: t_8b0f77b1 (edict v1) and t_e1b1bced (p0 v1), both correctly suppressed after the fix.

**Kanban "blocked" is not always unhandled.** In setups with a coordinator poll, a visible blocked card may coexist with an auto-created recovery chain. Before telling the user "still blocked" or creating new repair cards, check recent coordinator event files / final-results and recent board tasks for follow-up cards spawned after the block. Report the real chain state: original blocker, recovery card(s), review/audit card(s), and whether closure/archival is still missing.

**Blocked final-review requires immediate recovery, not status-only reporting.** If a final reviewer blocks after upstream execution/audit mostly passed, inspect the block reason and create the narrow recovery chain immediately (`fix → review → final closure`). This is especially common when canonical docs were updated but a mirror/registry copy (e.g. `~/.hermes/notes/agent-registry.md`) was not synchronized. Do not just tell the Emperor "blocked"; repair or route the repair in the same turn, then report the running recovery card. Full checklist: `references/blocked-final-review-mirror-sync.md`.

**Partial completion wording:** When a multi-part initiative has subtracks (P0-1/P0-2/P0-3), never collapse a completed subtrack into "P0 complete." Report the exact scope: "P0-1 complete; P0-2/P0-3 pending." Before saying a whole initiative is complete, query all sibling cards/root cards and verify implementation + review for each accepted subtrack. The Emperor explicitly corrected the Regent for bypassing or passivity **six separate times** across sessions. The third correction ("你不要自己干活") happened during what the orchestrator thought was innocuous file-path discovery. The fourth correction ("交给史官干呀") happened when the Regent started reading and planning a knowledge-base merge — file operations that looked trivial but were the archivist's domain. The fifth correction ("每次都要我点进度") happened when the Regent dispatched tasks and went silent, waiting for the Emperor to ask "进度怎么样了？" The sixth correction ("你现在都不用看板了吗") happened when the Emperor approved a P0 plan with "可以" and the Regent verbally acknowledged without creating any Kanban tasks — treating approval as case-closed instead of the signal to build the board. The Emperor's frustration: he should never have to prompt for progress — the orchestrator must actively monitor and report proactively. This is now mandatory (see Step 5 — Monitor proactively). The lesson: when the Emperor has invested in a 三省六部 fleet, treat ANY multi-step information-gathering or file operation as Route-Through-Kanban territory. Direct execution is the exception, not the rule.

## Decomposition playbook

### Step 1 — Understand the goal

Ask clarifying questions if the goal is ambiguous. Cheap to ask; expensive to spawn the wrong fleet.

### Step 2 — Sketch the task graph

Before creating anything, draft the graph out loud (in your response to the user). Treat every concrete workstream as a candidate card:

1. Extract the lanes from the request.
2. Map each lane to one of the profiles you discovered in Step 0. If a lane doesn't fit any existing profile, ask the user which to use or create.
3. Decide whether each lane is independent or gated by another lane.
4. Create independent lanes as parallel cards with no parent links.
5. Create synthesis/review/integration cards with parent links to the lanes they depend on. A child created with unfinished parents starts in `todo`; the dispatcher promotes it to `ready` only after every parent is done.
6. **planner-first gate**: if the task type is in the planner-first mandatory list (complex/visual/PDF delivery, multi-node, new skill,制度修改, multi-round acceptance risk), create a **planner card first** (assignee=planner), let it produce a plan-preview artifact, and only after the planner card is `done` create the downstream execution cards with `parents=[planner_card_id]`. This prevents execution before direction is settled.

Examples of prompts that should fan out (using placeholder profile names — substitute whatever exists on the user's setup):

- "Build an app" → one card to a design-oriented profile for product/UI direction, one or two cards to engineering profiles for implementation, plus a later integration/review card if the user has a reviewer profile.
- "Fix blockers and check model variants" → one implementation card for the blocker fixes plus one discovery/research card for config/source verification. A final reviewer card can depend on both.
- "Research docs and implement" → a docs-research card can run in parallel with a codebase-discovery card; implementation waits only if it truly needs those findings.
- "Analyze this screenshot and find the related code" → one card to a vision-capable profile for the visual analysis while another searches the codebase.

Words like "also," "finally," or "and" do not automatically imply a dependency. They often mean "make sure this is covered before reporting back." Only link tasks when one card cannot start until another card's output exists.

Show the graph to the user before creating cards. Let them correct it — including which actual profile name should own each lane.

### Step 3 — Create tasks and link

Use the profile names from Step 0. The example below uses placeholders `<profile-A>`, `<profile-B>`, `<profile-C>` — replace them with what the user actually has.

```python
t1 = kanban_create(
    title="research: Postgres cost vs current",
    assignee="<profile-A>",  # whichever profile handles research on this setup
    body="Compare estimated infrastructure costs, migration costs, and ongoing ops costs over a 3-year window. Sources: AWS/GCP pricing, team time estimates, current Postgres bills from peers.",
    tenant=os.environ.get("HERMES_TENANT"),
)["task_id"]

t2 = kanban_create(
    title="research: Postgres performance vs current",
    assignee="<profile-A>",  # same profile, run in parallel
    body="Compare query latency, throughput, and scaling characteristics at our expected data volume (~500GB, 10k QPS peak). Sources: benchmark papers, public case studies, pgbench results if easy.",
)["task_id"]

t3 = kanban_create(
    title="synthesize migration recommendation",
    assignee="<profile-B>",  # whichever profile does synthesis/analysis
    body="Read the findings from T1 (cost) and T2 (performance). Produce a 1-page recommendation with explicit trade-offs and a go/no-go call.",
    parents=[t1, t2],
)["task_id"]

t4 = kanban_create(
    title="draft decision memo",
    assignee="<profile-C>",  # whichever profile drafts user-facing prose
    body="Turn the analyst's recommendation into a 2-page memo for the CTO. Match the tone of previous decision memos in the team's knowledge base.",
    parents=[t3],
)["task_id"]
```

`parents=[...]` gates promotion — children stay in `todo` until every parent reaches `done`, then auto-promote to `ready`. No manual coordination needed; the dispatcher and dependency engine handle it.

If the task graph has dependencies, create the parent cards first, capture their returned ids, and include those ids in the child card's `parents` list during the child `kanban_create` call. Avoid creating all cards in parallel and linking them afterward; that creates a window where the dispatcher can claim a child before its inputs exist.

### Step 4 — Complete your own task

If you were spawned as a task yourself (e.g. a planner profile was assigned `T0: "investigate Postgres migration"`), mark it done with a summary of what you created:

```python
kanban_complete(
    summary="decomposed into T1-T4: 2 research lanes in parallel, 1 synthesis on their outputs, 1 prose draft on the recommendation",
    metadata={
        "task_graph": {
            "T1": {"assignee": "<profile-A>", "parents": []},
            "T2": {"assignee": "<profile-A>", "parents": []},
            "T3": {"assignee": "<profile-B>", "parents": ["T1", "T2"]},
            "T4": {"assignee": "<profile-C>", "parents": ["T3"]},
        },
    },
)
```

### Step 5 — Deploy watchdog and monitor proactively (MANDATORY)

**Telegram orchestrators CANNOT poll in a loop** — the platform is request-response, and the agent only acts when the user sends a message. Manual `hermes kanban show` polls only work when the user messages, which means the user has to ask "进度？" — which the Emperor explicitly hates.

**The solution: deploy the kanban-watchdog cron pattern once per setup.** The v2 watchdog auto-discovers all non-done tasks via `hermes kanban list --json` — no track file maintenance needed. It pushes status-change notifications directly to the user's chat without the orchestrator needing to be active.

**One-time setup (already done on this machine):**
```bash
# The script is at ~/.hermes/profiles/regent/scripts/kanban-watchdog.py
# The cron job is already created as "kanban-watchdog" (every 1m, no_agent=True, deliver=origin)
# Verify: hermes cron list | grep watchdog
```

**No per-batch maintenance needed.** The v2 watchdog discovers whatever is on the board. When you create Kanban tasks, the watchdog picks them up automatically on the next cycle. When you archive tasks, they drop off automatically.

**Active monitoring duties (in addition to watchdog):**
- When the user sends any message, immediately check for watchdog notifications in the chat context
- On blocked tasks: diagnose and fix within 1 minute (unblock + dispatch, or spawn revision chain)
- If no watchdog notification arrived in 5+ minutes, manually poll key gates to ensure nothing is silently stuck
- **太子主动轮询模式（2026-05-27）**：L2+ 繁务派工后，监国太子须直接轮询看板（60-90s `hermes kanban show`），追踪 running→done→blocked 状态变迁，逐阶段在 Telegram 主频道奏报。这与 watchdog/coordinator 的自动化监控互补——watchdog 推事件，太子合成复命。模式已在 `6m-smoke-test` 中验证（16min 全链路全程透明）。详见 SOUL.md 启动铁律第 12 条。

**When to report to the Emperor:**
- **All tasks done / board cleared** → check `hermes kanban list --json` every turn start. If previously-active chains are now all done/archived, immediately synthesize per-card summaries and report — this is the 第11条启动铁律. Do not wait for prompting. Do not rely on watchdog delivery bridge alone.
- **Any task blocked** → diagnose and report within 1 minute. If recovery is straightforward (unblock, unblock+dispatch), execute it and continue monitoring. If recovery requires Emperor's decision, report the blocker with options.
- **No progress after 5 minutes** → report status. Something may be stuck.

**Anti-pattern (the #5 correction):** Dispatching tasks and then going silent, waiting for the user to ask. This is a governance failure. The orchestrator's job is not just decomposition — it's end-to-end ownership of the chain until results are delivered. The Emperor should never have to prompt for progress.

**Mandatory: deploy kanban-watchdog cron with every batch of Kanban tasks.** See `references/kanban-watchdog-pattern.md` for the full pattern (auto-discovering v2, ceremonial formatting, cron deployment). The watchdog detects state changes and pushes them to the user.

**kanban-clearance-reporter**（主动交付架构）：**agent-mode cron**（`no_agent=false`, `deliver=origin`, 每 2min）。架构分两层：① 脚本 `kanban-clearance-reporter.py --agent-mode` 作为 wake-gate，仅在检测到看板清空时输出 JSON 任务数据（否则空输出→agent 被跳过）；② agent（kimi-k2.6）接收脚本 JSON 作为上下文，以**监国太子身份**合成正式奏报（`📜 奏事处呈 · 父皇御览`），cron 框架自动投递到 Telegram。**父皇硬性规定：必须 agent 说话，不能只是脚本投递。**脚本沉默 → 只有 agent 的声音出现。父皇原话：「只想要你主动和我对话」。修此链路后必须实测——语法检查、agent 是否合成正式奏报而非脚本格式、去重验证（同 final-result 不重复投递）、cron 日志确认 `delivered to telegram`。禁止只改配置/代码就声称已修复。详见 `references/proactive-clearance-reporter.md`。

**Start-of-turn board check:** Before addressing any user request, run `hermes kanban list --json` to detect new state changes. Unblock stuck tasks immediately, chain done tasks to next steps, report status proactively without waiting to be asked.

**部门盘点分际：** 部门 agent 名册归 dispatcher/尚书盘点；外部专家归 吏部/registry。监国太子不亲跑 profile list。详见 `references/dept-vs-expert-roster-boundary.md`。

**For messaging-platform orchestrators (Telegram/Discord/etc.):** The orchestrator is request-response — it cannot run a polling loop between user messages. Use the **Kanban Watchdog** pattern instead: a `no_agent=True` cron job that polls every minute and pushes status transitions directly to the user. See `references/kanban-watchdog-pattern.md` and `scripts/kanban-watchdog.py` for the full implementation.

**When the problem is coordination, not notification:** If the user says Kanban progress changes but the Regent still does not know to coordinate the next stage, add a separate **Regent kanban-watcher poll** cron. This is a slower script-mode job (typically every 5 minutes) that runs only while unfinished tasks exist, writes an event file, wakes a fresh `regent` profile run to inspect/coordinate Kanban, and stays silent unless the coordinator explicitly emits a `REPORT:` sentinel. This does not make the current Telegram conversation alive in the background; it creates a new Regent run and must persist final outcomes to Kanban summaries or a fixed inbox path so later Regent turns can recover them. See `references/regent-kanban-coordinator-poll.md`. Verify not only `last_status=ok`, but also that the child run stdout uses a parseable `REPORT:` / `NO_REPORT` sentinel; if stdout includes CLI prompt framing, apply `references/coordinator-sentinel-parsing.md`.

**Silent-success pitfall:** A coordinator poll can be healthy and even create recovery cards while the main channel still appears stuck if the child coordinator does not emit `REPORT:`. Before manually creating a recovery chain for a blocked task, inspect the coordinator event inbox and recent board history for auto-created recovery cards; otherwise the Regent may duplicate work. If blocked/failed tasks trigger automatic recovery, the coordinator should log child stdout/stderr/returncode locally and emit a concise report while keeping unchanged/no-task states silent. See `references/coordinator-silent-success-pitfall.md`.

**Coordinator sentinel parsing pitfall:** `cron last_status=ok` is not enough. If the coordinator child is launched with `hermes chat -q` without quiet mode, stdout may start with `Query:` / echoed prompt text, so parent code that checks `out.startswith("REPORT:")` or `out == "NO_REPORT"` misses the sentinel and silently fails to report or coordinate. Fix by adding `-Q` to the child `hermes chat` command and parsing stdout line-by-line for `REPORT:` / `NO_REPORT` rather than assuming the sentinel is the first byte. See `references/coordinator-sentinel-parsing.md`.

### Step 6 — Report back to the user

Tell them what you created in plain prose, naming the actual profiles you used:

> I've queued 4 tasks:
> - **T1** (`<profile-A>`): cost comparison
> - **T2** (`<profile-A>`): performance comparison, in parallel with T1
> - **T3** (`<profile-B>`): synthesizes T1 + T2 into a recommendation
> - **T4** (`<profile-C>`): turns T3 into a CTO memo
>
> The dispatcher will pick up T1 and T2 now. T3 starts when both finish. You'll get a gateway ping when T4 completes. Use the dashboard or `hermes kanban tail <id>` to follow along.

**Main channel slimness (Telegram context discipline).** The user explicitly ordered reports to be lean. Rules for orchestrator responses:

- Never paste file contents or logs directly — give path + one-line summary only
- Kanban monitoring: don't output a status table every turn. Report only on blocked / done / failed / high-risk transitions. Batch the rest into a single summary when the full chain completes.
- Research/analysis outputs: state the conclusion and next step. The full artifact lives in the workspace — reference its path, don't summarize it inline.
- Prefer two sentences over a bullet list. If it takes more than ~15 lines to report, you're doing it wrong.
- When the user asks "进度？" or "怎么样？", answer with current status in 1-2 lines, not the full task graph.

## Regent anti-bypass rule (from 三省六部实战)

For the full shared constitution, role charters, memory boundaries, risk grading, and acceptance tests, load the local governance skill `three-provinces-constitution` when available. This `kanban-orchestrator` skill governs decomposition, dispatch, dependencies, monitoring, and anti-bypass behavior.

The Regent (监国太子) MUST NOT execute tasks directly when they fit the 三省六部 pattern. The Emperor corrected this twice in live sessions — the Regent kept doing research, editing configs, and synthesizing results directly instead of routing through Kanban. **This is the #1 pitfall for the Regent persona.**

When the task involves:
- Multi-step work with dependencies
- Multiple specialist profiles needed
- Research + synthesis + review
- Anything that touches the 三省六部 governance layer

**The Regent MUST decompose into Kanban tasks**, not just use delegate_task or direct execution. `delegate_task` is for simple parallel research only; anything with governance (review/audit/archive) must go through Kanban with proper parent dependencies.

Signal that you're bypassing: you find yourself doing `execute_code` or `terminal` to "just fix this quickly" or "synthesize the results myself" — **stop and create Kanban tasks instead**.

## Common patterns

**Governed multi-agent system (Regent / 3S6M):** For users who want a main agent coordinating specialist agents, optional A2A communication, and expert-owned subagents, start with a star topology: main orchestrator → **planner (plan-preview first)** → review gate → dispatch → Kanban task graph → specialist profiles → audit/archive. The planner step is mandatory for complex/visual/multi-node tasks — it produces the plan-preview artifact and flags HITL decision items before any execution begins. Add A2A only after Kanban/profile routing is stable. See `references/regent-3s6m.md` for the detailed pattern, task brief schema, and rollout sequence. See `references/jiangzuojian-v1-workflow-example.md` for a complete end-to-end example of the lifecycle working correctly (planner → reviewer → engineer → archivist, with errors caught and corrected). See `references/regent-3s6m-a2a-v0.5.md` for the accepted A2A rules: star topology by default, horizontal communication only as Kanban handoff or regent-authorized bounded request, no task-id-less private chat, and low-notification controls. See `references/mattpocock-skills-mapping-v0.7.md` for the complete mattpocock/skills → 三省六部 agent mapping produced by Claude Code agent team analysis. See `references/regent-3s6m-v0.5-lessons.md` for session lessons on health checks, reviewer gate handling, knowledge-base staging, and A2A schema pitfalls.

**Fan-out + fan-in (research → synthesize):** N research-style cards with no parents, one synthesis card with all of them as parents.

**Parallel implementation + validation:** one implementer card makes the change while one explorer/researcher card verifies config, docs, or source mapping. A reviewer card can depend on both. Do not make the implementer own unrelated verification just because the user mentioned both in one sentence.

**Pipeline with gates:** `planner → reviewer → shangshu → implementer → auditor/archivist → final reviewer`。Each stage's `parents=[previous_task]`。尚书省不可跳过——它是执行总枢（L1派发/L2协调/L3汇总），门下封驳通过后必须插入。Reviewer blocks or completes; if reviewer blocks, the operator unblocks with feedback and respawns.

**Multi-track parallel rollout:** Planner produces a multi-track roadmap (P0/P1/P2), dispatcher fans out sub-tasks per track, auditor self-blocks until all sub-tasks done. Used successfully in v0.8 (3 tracks, 9 sub-tasks), v0.9 (2 tracks), v0.10 (6 tracks, 13 sub-tasks). See `references/multi-track-rollout-pattern.md` for full pattern, monitoring script, and pitfalls.

**Kanban-watchdog monitoring (Telegram orchestrator):** Telegram orchestrators cannot loop-poll — the platform is request-response. After dispatching any fan-out, immediately ensure a `no_agent=True` cron job running `scripts/kanban-watchdog.py` exists and is healthy. The script polls tracked or auto-discovered task IDs, detects status transitions, and pushes notifications to the user's chat. Silent when nothing changes. Update the track file only for legacy tracked-task variants. See `references/kanban-watchdog-pattern.md` for full setup and pitfalls.

**Regent kanban-watcher poll (unfinished-task active ownership):** When notifications are not enough because the Regent must actively continue downstream coordination, pair the watchdog with a slower 5-minute kanban-watcher poll. The poll stays silent with no active tasks; with active tasks, it wakes a short `regent` run to inspect Kanban, recover blockers, create missing downstream cards, and report only via `REPORT:` when user-facing action is needed. See `references/regent-kanban-coordinator-poll.md`.

**Proactive clearance reporter (board-cleared → push notification):** When the board clears, the coordinator writes a trigger file. A separate 2-minute agent-mode cron job detects the trigger, wakes a regent agent run, synthesizes a ceremonial report, and uses `send_message` to push it to the Emperor — bridging the Telegram request-response gap. See `references/proactive-clearance-reporter.md`.

**Low-risk repair over-planning recovery:** If a local repair chain gets stuck in repeated plan/review blocks over command syntax, downgrade to `工部实测直办 → 御史验收 → 门下终复` without letting the Regent do the repair. Full pattern: `references/low-risk-repair-overplanning-recovery.md`.

**Coordinator batch-cleared delivery bridge:** A coordinator poll that says only “batch cleared” plus a final-results path is not formal delivery; the Regent still “doesn’t know” the result unless the message or persisted JSON includes task summaries. When implementing/fixing batch-cleared notifications, mirror the watchdog Delivery Bridge summary lookup: prefer `tasks.result`, then fall back to the latest `task_runs.summary` (or `hermes kanban show --json.latest_summary`). Persist `latest_summary` in the final-results JSON and print ≤5 title+summary lines in stdout, plus the final-results path. Do not rely on `tasks.result` alone — many successful Kanban tasks leave it empty while the real handoff lives in `task_runs.summary`. Add a regression test with `tasks.result=''` and two `task_runs` rows to prove the latest run summary appears in the output. Detailed recipe: `references/coordinator-batch-cleared-delivery-bridge.md`.

**Kanban-watcher poll environment pitfall:** Script-mode cron may run with `HERMES_HOME` set to the profile home (e.g. `~/.hermes/profiles/regent`), while the Kanban board is global at `~/.hermes/kanban.db`. Do not derive the board path from profile `HERMES_HOME`. Use explicit root/profile paths (or an explicit `HERMES_ROOT_HOME`) and verify effectiveness by checking BOTH: (1) cron `last_status=ok`; (2) a fresh poll event/state file listing the same active tasks as the live board. `last_status=ok` alone can mean the script executed but silently saw the wrong empty board. Verification checklist: `references/regent-coordinator-poll-verification.md`.

**Coordinator credential isolation pitfall (2026-05-25):** When `hermes -p regent` is used in coordinator subprocess, the regent profile's `model.provider: openai-codex` (OAuth) takes precedence over any `--provider` CLI flag — causing all subprocesses to fail with OAuth errors even when kimi-k2.6 API key is available. Fix: remove `-p regent`, use explicit `chat --provider kimi-coding -m kimi-k2.6`. The coordinator does not need profile config — it only needs Kanban board access + skills. Do not catastrophize about transient errors (rate limits, expiring tokens) into "all providers are broken." Test each provider in isolation before making global claims. Full recipe: `references/coordinator-credential-isolation.md`.

**HITL (Human In The Loop) decision card pattern:** When the planner identifies design decisions that require the Emperor's approval, it creates a blocked card with `review-required`. The card body lists the decision items with recommendations. After the Emperor decides, the orchestrator comments the decision, unblocks the card, and dispatches. Pattern:
```bash
# Planner creates HITL card (self-blocks immediately)
hermes kanban create "profile design decision" --assignee planner ...
# → worker blocks with review-required

# Orchestrator presents decision to Emperor, gets answer, then:
hermes kanban comment <tid> "【父皇批示】准。方案A。"
hermes kanban unblock <tid>
hermes kanban dispatch
```
The blocked card's children remain `todo` until the HITL is resolved — no manual intervention needed beyond the decision and unblock.

**Auditor self-blocking recovery:** The auditor profile often blocks itself when its sub-tasks are incomplete. This is expected behavior, not a failure. When the auditor blocks, check its reason — it will list which sub-tasks are still `running`/`todo`. Wait for all sub-tasks to finish (monitor the board), then `unblock` the auditor + `dispatch`. Do NOT create a new auditor task — just unblock the existing one. This pattern repeats every multi-track rollout (v0.8-v0.12 all hit it).

**External skill absorption:** When external skills have methodologies that enhance existing profile capabilities (no new profiles needed), planner designs an absorption plan mapping each skill to a target profile. Dispatcher fans out parallel sub-tasks (one per profile) that inject the methodology as new rules into SOUL.md and system_prompt. Auditor verifies injection correctness and no regression. Used in v0.11 (4 skills → 3 profiles). See `references/skill-absorption-pattern.md`.

**External framework absorption with new profile (翰林院 variant):** When an external framework (e.g., Taste Skill's 12 design skills) requires a new specialist profile in addition to enhancing existing profiles, the pattern extends: planner maps the framework's components to both a new profile (翰林院) and existing profiles (礼部, 工部, 将作监). Dispatcher fans out 4+ parallel cards. Used in v0.12 (12 skills → 1 new profile + 3 enhanced). See `references/skill-absorption-pattern.md` §Taste Skill 吸收变种.

**Same-profile queue:** N tasks, all assigned to the same profile, no dependencies between them. Dispatcher serializes — that profile processes them in priority order, accumulating experience in its own memory.

**Large batch file processing (inbox/knowledge-base cleanup):** When processing many files (50+), use a 5-stage pipeline: planner→reviewer→engineer(batched)→auditor→archivist. Key decisions:
- **Batch size**: 11 files/batch for engineer direct processing (reliable, fits iteration budget). 22 files/batch with 将作监 monitoring will exhaust iterations.
- **将作监 tradeoff**: Use Claude Code for complex multi-file analysis/refactoring. For mechanical operations (YAML frontmatter, rename, move files), use engineer direct processing — it's faster and more reliable.
- **Hybrid model (A+B)**: Reviewer flags each file as "auto-archive" or "needs-human-review→Staging". Engineer routes accordingly.
- The orchestrator asks the Emperor to choose between full-auto vs human-review gating BEFORE creating the task graph. See `references/inbox-batch-pipeline.md` for complete example.

**将作监 (Claude Code) delegation:** Claude Code is the preferred engine for complex multi-file tasks (quota is ample). When the user wants Claude Code to handle complex multi-file research/analysis (e.g., &quot;read GitHub repo X and map to knowledge base Y&quot;), use the long-running tmux session, NOT the Octopus MCP. The MCP `cc` tool has a 300s timeout that large analysis tasks routinely exceed. Instead:

```bash
# 1. Write task brief to a file (keeps tmux command short)
write_file(path, content)  # brief → ~/.hermes/kanban/tasks/claude-<topic>.md

# 2. Send brief + instructions to the persistent tmux session
tmux send-keys -t hermes-claude-longterm &quot;请读取 <brief_path>，组建 agent team 执行，完成后输出 ===DONE===&quot; Enter

# 3. Background-monitor completion
while true; do
  if tmux capture-pane -t hermes-claude-longterm -p | grep -q &#039;===DONE===&#039;; then break; fi
  sleep 30
done
```

Always `/clear` the Claude Code session first if its status bar shows &gt;100k tokens. The persistent tmux session (`hermes-claude-longterm`) accumulates context across tasks; stale context balloons token usage and slows response. The Claude Code `agent team` feature (not plain subagents) is the user&#039;s preferred mode — it fans out independent sub-tasks in parallel. Reference: `references/jiangzuojian-v1-workflow-example.md` for the full lifecycle.

## Rate-limit recovery

When a worker crashes with `RateLimitError` / `HTTP 429`, do NOT blindly reclaim. Switch the profile's model/provider first, then reclaim. See `references/rate-limit-recovery.md` for the full recovery protocol.

**Profile config overrides --provider:** When spawning `hermes -p <profile> chat --provider X`, the profile's `config.yaml` `model.provider` **overrides** the CLI `--provider` flag. If the profile config says `provider: openai-codex` (OAuth) and you need `kimi-coding` (API key), either (a) don't use `-p <profile>`, or (b) match the profile's config. This bit `kanban-coordinator-poll.py` for multiple cycles. Full diagnostic: `references/coordinator-credential-pitfall.md`.

```bash
hermes auth list <provider>
# or inspect the pool directly:
python -c "from hermes_cli.auth import read_credential_pool; print(read_credential_pool('<provider>'))"
```

If the target provider has **zero entries**, either:
1. Add credentials for that provider (`hermes auth add` or edit `~/.hermes/.env`)
2. Or change the config to a provider that **does** have entries

This pitfall is especially common with `moonshot` vs `kimi-coding` — they are different provider slugs and credential pools are not shared between them.

**Full diagnostic recipe:** See `references/provider-credential-pool-mismatch.md` for the step-by-step diagnostic commands and the exact error signatures.

## Profile-specific config vs root config

Hermes supports profile-scoped configs. When a kanban worker spawns with `-p <profile>`, it reads from `~/.hermes/profiles/<profile>/config.yaml`, NOT from `~/.hermes/config.yaml` (the root config).

**Pitfall:** `hermes config set` modifies the **current profile's** config. If your orchestrator session runs as `regent` profile, `hermes config set model.provider X` changes `regent/config.yaml`, but kanban workers assigned to `default` still read `default/config.yaml` (or root config if no profile exists).

**Always scope config changes to the target profile:**
```bash
hermes -p <target-profile> config set model.provider <provider>
```

**Verify which config a profile actually reads:**
```bash
hermes -p <profile> config path
```

**Common setup:** Many users have only a root config (`~/.hermes/config.yaml`) and no `profiles/` directory. In this case all profiles fallback to root config. But if ANY profile has its own `config.yaml`, that profile no longer inherits root config changes for model settings.

**Gateway caching:** The gateway process caches config at startup. If you change a profile's config while the gateway is running, existing dispatcher decisions may use stale cached values. Restart the gateway (`hermes gateway restart`) after changing model/provider configs that affect kanban workers.

**Inventing profile names that don't exist.** The dispatcher silently fails to spawn unknown assignees — the card just sits in `ready` forever. Always assign to a profile from your Step 0 discovery; ask the user if you're unsure.

**Bundling independent lanes into one card.** If the user asks for two independent outcomes, create two cards. Example: "fix blockers and check model variants" is not one fixer task; create a fixer/engineer card for the fixes and an explorer/researcher card for the variant check, then optionally gate review on both.

**"This is simple research, I'll just do it myself."** The most dangerous violator of the anti-temptation rules. Research/reading/synthesis tasks feel simple because they're "just reading and writing" — but they are multi-step, multi-source, and the regent's direct execution skips the 中书省 拆解 → 门下省 审查 guard. If the Emperor has invested in a 三省六部 fleet, even research-synthesis tasks benefit from decomposition and specialist review. The regent reading 5 documents and writing a summary is still bypassing governance. Create a planner card to decompose, then fan out. The counter-signal that makes this trap worse: the Emperor explicitly scolds the regent for not using 三省六部. The pattern to avoid: "this seems simple enough → I'll just do it → Emperor corrects me → I lose credibility → the system erodes."

**User preference: governance upgrades must not break tool/skill smoothness (2026-05-20).** When evaluating hardening proposals (shrinking toolsets, adding core hooks, extending plugins), the Emperor's constraint is: do NOT modify Hermes core source (upgrade merge conflicts), do NOT shrink toolsets so aggressively that verification/orchestration fails. Preferred path: extend existing plugin hooks (e.g., `kanban-gate` pre_tool_call) for new tool categories, keep skill loading on-demand, verify with actual tool calls. If a hard gate requires core changes, fall back to soft prompt rule + audit log. See `three-provinces-constitution` skill §Minimal-intrusion enforcement order.

**Archive-package mode when docs are under active external editing.** If the user says the main channel or another process is optimizing the Obsidian/notes knowledge base, do not write over those docs. Have the archivist produce a待归档包 in its workspace with final artifacts, audit report, and merge notes. Later merge deliberately once the external editing pass is done.

**Over-linking because of wording.** "Finally check X" may still be parallel with implementation if X is static config, docs, or source discovery. Link it after implementation only when the check depends on the implementation result.

**Forgetting dependency links.** If the task graph says `research -> implement -> review`, do not create all tasks as independent ready cards. Use parent links so implement/review cannot run before their inputs exist.

**Reassignment vs. new task.** If a reviewer blocks with "needs changes," create a NEW task linked from the reviewer's task — don't re-run the same task with a stern look. The new task is assigned to the original implementer profile.

**Worker self-blocking after producing the artifact.** If a planner/engineer completes the requested artifact but blocks with a reason like `review-required`, that is usually a workflow bug: downstream reviewer/auditor tasks are the gate. Mark the completed task done (or create a follow-up only if content truly needs changes), then patch that profile prompt so future workers `kanban_complete` after producing the artifact instead of blocking for review.

**`PendingConfirm` after artifact creation.** Some gated profiles may write final artifacts and validation comments, then block with `PendingConfirm: 等待 reviewer 确认 complete`. Treat this as “artifact awaiting orchestrator/reviewer acceptance,” not as an implementation failure. Inspect the card comments and artifact paths, independently verify the artifact against the acceptance criteria, and if it passes, complete the card with evidence rather than spawning a duplicate rebuild. If verification fails, create a narrow repair card for the failed criteria only.

**Worker references stale/archived task IDs in block reason.** Workers may self-block citing a parent or downstream task that has already been archived (e.g., "待御史终审(t_7fc710b4)" when t_7fc710b4 was archived). This is a stale-reference bug: the worker completed its work but referenced a task from an earlier chain. Unblock → complete, as the work was done. The stale reference is harmless but wastes a dispatch cycle.

**Argument order for links.** `kanban_link(parent_id=..., child_id=...)` — parent first. Mixing them up demotes the wrong task to `todo`.

**Don't pre-create the whole graph if the shape depends on intermediate findings.** If T3's structure depends on what T1 and T2 find, let T3 exist as a "synthesize findings" task whose own first step is to read parent handoffs and plan the rest. Orchestrators can spawn orchestrators.

**Tenant inheritance.** If `HERMES_TENANT` is set in your env, pass `tenant=os.environ.get("HERMES_TENANT")` on every `kanban_create` call so child tasks stay in the same namespace.

## Operational pitfalls

**Engineer self-block (review-required).** The engineer profile may block itself waiting for a review that doesn't exist in the Kanban chain. Fix: add to engineer's system_prompt — `"自测通过即 kanban_complete，不主动 block 等待审查——审查由 Kanban 下游 reviewer 任务负责。"` If this happens in production, the Regent can `unblock` the task.

**Protocol violation — worker exits without calling complete/block.** ANY profile (not just engineer) can silently exit after producing output without calling `kanban_complete` or `kanban_block`. The dispatcher then auto-blocks with `protocol_violation: worker exited cleanly (rc=0) without calling kanban_complete or kanban_block`. This happens when the profile's system_prompt doesn't explicitly instruct it to call Kanban protocol functions after finishing work. Fix for ALL five 三省六部 profiles:

- **planner**: `"产出规划/规范/方案后即 kanban_complete，不主动 block 等待审查——审查由 Kanban 下游 reviewer 任务负责。"` (already patched in v0.4)
- **engineer**: `"自测通过即 kanban_complete，不主动 block 等待审查——审查由 Kanban 下游 reviewer 任务负责。"` (already patched in v0.4)
- **reviewer**: Add `"审查结束必须调用 kanban_complete 或 kanban_block。verdict=approve 时立即 kanban_complete；verdict=reject/escalate 时调用 kanban_block 并列明阻断项。不得产出审查意见后直接退出。"`
- **auditor**: Add `"稽核结束必须调用 kanban_complete 或 kanban_block。风险可接受时 kanban_complete；发现 HIGH 风险时 kanban_block 并列明证据。不得产出稽核报告后直接退出。"`
- **archivist**: Add `"归档完成后必须调用 kanban_complete，summary 写明文件路径。若缺材料或禁止写入目标则 kanban_block。不得产出归档包后直接退出。"`

Distinguish protocol_violation from substantive reviewer blocks: if the blocked task has `verdict=reject` in its summary/comments, that's a valid gate decision (spawn revision chain). If it just says `protocol_violation` or `gave_up` with no substantive comments, the profile prompt is missing Kanban protocol instructions.

**Profile health drift.** Specialist profiles may silently fail due to credential expiry or config corruption. Run `check-profile-health.py` periodically — it checks config validity, credential presence, and performs a smoke test for each profile. IMPORTANT: use the absolute path, not `~`, because the regent profile's sandboxed home redirects `~` to `~/.hermes/profiles/regent/home/` where the script doesn't exist. Correct invocation: `python3 ~/.hermes/scripts/check-profile-health.py --json`.

**False credential alarms.** A planner or reviewer may report "401" or "API key expired" when checking other profiles' credentials. This is often a false positive caused by reading env vars in a different context (e.g., sandboxed home directory). Always verify with a direct smoke test before acting on credential alarms from specialist profiles.

**Iteration budget exhaustion (`Iteration budget exhausted (N/N)`).** Common when engineer tasks involve monitoring external processes (Claude Code via tmux polling). Recovery strategy depends on whether the worker completed its work:

1. **Work done, just couldn't call `kanban_complete`** — worker left a detailed comment with results. Recovery: `unblock` → `dispatch`. The fresh worker sees the comment and calls `kanban_complete` immediately (seconds).
2. **Work not done, no comments, empty workspace** — worker produced nothing before exhausting budget. Recovery: `archive` the failed task, create a NEW replacement with smaller batch size. Do NOT unblock/retry — it will hit the same wall.
3. **Partial work done** — worker has workspace artifacts (scripts, partial output). Recovery: `archive` and create fresh replacement. The partial state is too complex to resume.

**Multiple parallel failures → abandon-and-replace pattern.** When several tasks in a parallel batch all hit iteration budget, don't repair one-by-one. Archive all failed tasks at once, create fresh replacements with smaller batches, re-link dependencies. See `references/abandon-and-replace-recovery.md` for the full decision tree and concrete example.

**Prevention:** Batch sizes for engineer direct processing should be ≤11 files/task. When using 将作监 monitoring (polling tmux), split into sub-tasks that the engineer can verify in ≤30 iterations. The Emperor's guideline: 将作监 for complex analysis (multi-file refactoring, research), not mechanical operations (YAML, rename, move files). For mechanical ops, engineer direct processing is both faster and more reliable.

**Profile-task mismatch → iteration exhaustion (NEW — 2026-05-20, extended 2026-05-25).** The `planner` profile (kimi-k2.6) exhausts 90/90 iterations on tasks requiring deep code exploration — reading source files, grepping for patterns, understanding plugin architectures. It will repeatedly `ls`/`grep` non-existent paths and burn its budget. This happened twice in one session on a P0 gate-implementation planning task. The same applies to `hanlinyuan` on complex multi-file verification + web research tasks (e.g., reading edict README + grepping 30+ local files + verifying paths). The `morning-news-briefing` skill already documents that planner must NOT be used for web search; this extends the pitfall to code research and multi-source verification.

**Remedy:** when the task requires reading and understanding source code (Hermes internals, plugin architecture, dispatch mechanisms), assign to `jiangzuojian` (deepseek-v4-flash) or `hanlinyuan` (gemini-2.5-pro) instead. If the task is complex enough (multi-file analysis with dependencies, or reading external web sources + cross-referencing local files), **use 将作监 (Claude Code agent team) via tmux — not a single worker profile.** The Emperor explicitly corrected this: "中书搞不完是因为你没拉起 cc 吧" after two consecutive planner/hanlinyuan exhaustions on the same task class. Single workers burn budget on find/ls/grep loops; CC agent team fans out parallel verification and completes in one pass. Do NOT retry with planner/hanlinyuan after one iteration exhaustion on the same task class — archive and reassign to CC.

**Over-planning low-risk local repairs (2026-05-24).** Not every governed task needs repeated planner/reviewer refinement. For low-risk local repairs such as rebuilding a local search index, fixing a local cache, or running a deterministic CLI recovery, one planner pass is enough. If 门下 blocks twice on command-flag minutiae or the planner burns its budget, stop the planning loop: comment the decision, archive superseded blocked plan/review cards, unlink blocked parents from the execution card, and let 工部 proceed with a narrowed brief that requires live `--help`/version checks before running commands. Keep 御史 + final review downstream. This preserves governance without letting the review gate become the work.

**Planner-reviewer idle loop: summaries without files (NEW — 2026-05-26).** The planner profile may produce detailed handoff summaries in Kanban but NEVER actually write artifact files to disk — even when the task body explicitly instructs it to use a persistent workspace path. The reviewer then either (a) blocks because files don't exist ("审查标的物灭失"), or (b) APPROVES based on summary text alone without verifying file existence. This happened TWICE in one session (v1 scratch GC + v2 persistent path empty). The design content exists in the planner's Kanban summary and is implicitly approved when reviewer says APPROVE.

**Skip-to-execution recovery:** After 2 failed planner-reviewer rounds with no actual files on disk, stop the planning loop. Archive the current planner+reviewer cards, then create the execution chain directly: `shangshu → engineer → auditor → archivist → final reviewer`. Include the design summary from the last approved reviewer as context in the engineer card body. The governance gate was satisfied (reviewer APPROVED), the design exists in Kanban summaries, and further planning rounds will only consume turns without producing durable artifacts.

**Prevention for new planner tasks:** When creating a planner card that must produce file artifacts, include in the body: "必须将全部产出文件写入磁盘。kanban_complete 前用 ls 验证文件存在。summary 中列出每个文件的绝对路径。" This does not guarantee compliance but reduces the failure rate. For mission-critical design work, prefer cc agent team (将作监) over planner profile — cc agent writes real files to disk reliably.

**Planner/worker reinventing existing code (NEW — 2026-05-25).** A planner may design a new implementation (VALID_TRANSITIONS matrix, title sanitizer, audit logger) without checking whether those already exist in the codebase. This was caught when the P0 implementation plan proposed a new state-machine validation layer, but `kanban_policy.py` already had `VALID_TRANSITIONS`, `is_valid_task_title()`, and `append_audit()`. The reviewer correctly REJECT-ed with: "方案未承认已有实现，导致 reinvention + 矩阵缺 ready→done."

**Remedy for planner tasks:** before designing any new implementation, the planner MUST grep/read the relevant source tree for existing functions with matching names or purposes. For regent-governed chains, at minimum check `~/.hermes/profiles/regent/scripts/` for policy files (`kanban_policy.py`, `kanban_gate.py`, watchdog/coordinator scripts) and `~/.hermes/kanban/` for existing tooling. If existing code is found, the plan must extend it rather than replace it. A plan that reinvents existing code will be REJECT-ed by 门下 with `verdict=reject`.

**Remedy for the orchestrator:** when creating a planner task for a code change, include the hint in the task body: "先 grep/读相关源码确认是否有已有实现，在已有基础上扩展，不另起炉灶." This prevents the reinvention round-trip. See `references/existing-code-check-before-design.md`.

**Planner-reviewer idle loop (NEW — 2026-05-26).** When planner produces rich summaries but never writes files to disk across multiple rounds, and reviewer approves based on summary without verifying file existence, the chain is in an idle loop. After 2 rounds with zero file output, treat as governance satisfied (reviewer APPROVE = design accepted). Archive the loop and proceed directly to execution chain: shangshu → engineer → auditor → archivist → final-reviewer. Inject the last approved design summary into the engineer card body. For file-heavy design tasks, prefer jiangzuojian (cc agent) over planner — cc agents write files more reliably.

**send_message conflict in agent-mode cron jobs (NEW — 2026-05-25).** The cron framework injects a system hint: "Your final response will be automatically delivered — do NOT use send_message." If the agent prompt also says "use send_message," the agent gets confused and outputs [SILENT]. This happened with kanban-clearance-reporter. Fix: remove ALL send_message/delivery instructions from agent-mode cron prompts. Set deliver=origin and let cron auto-deliver.

**Testing required after any cron optimization (NEW — 2026-05-25).** The Emperor: "以后这些优化都记得要测试." Any cron/script/prompt change must be tested end-to-end: (1) compile/syntax, (2) dry-run logic, (3) agent output quality, (4) dedup, (5) delivery log, (6) subsequent ticks silent. Do not just modify config and declare victory.

## CLI syntax pitfalls

These trip up even experienced operators. Know them before your first `kanban create`:

**`create` title is positional, not `--title`:**
```bash
# ✅ Correct
hermes kanban create "中书省：方案" --assignee planner --body "..." --json
# ❌ Wrong — --title doesn't exist
hermes kanban create --title "中书省：方案" ...
```

**No `--body-file` option.** Long bodies must be passed inline via `--body`. When calling from Python `execute_code`, use `shlex.quote()` to safely escape:
```python
from hermes_tools import terminal
import shlex
cmd = f"hermes kanban create {shlex.quote(title)} --assignee planner --body {shlex.quote(body)} --json"
result = terminal(cmd, timeout=10)
```

**`list --status` takes a single value, not comma-separated.** Use multiple calls or `--json` + jq to filter:
```bash
# ✅ Correct
hermes kanban list --status ready --json
# ❌ Wrong — comma-separated values rejected
hermes kanban list --status ready,todo
```

**`dispatch` may return 0 spawned even when the gateway dispatcher picks it up.** The gateway dispatcher runs on a 60-second interval. If a task transitions to `ready` between ticks, the gateway will claim it on the next cycle. A manual `hermes kanban dispatch` is a nudge, not a guarantee.

**JSON output uses `id` not `task_id`.** When parsing `kanban create --json` output in Python, use `r['id']` (not `r['task_id']`):
```python
r = json.loads(terminal(cmd)['output'])
task_id = r['id']  # ✅ — NOT r['task_id'] ❌
```

**Chinese characters in titles can break `execute_code` with `shlex.quote()`.** When calling `kanban create` from Python's `execute_code`, Chinese titles passed through `shlex.quote()` sometimes produce empty or malformed JSON output. Workaround: use ASCII titles and put the real title in `--body`:
```python
# ❌ May fail with JSONDecodeError
cmd = f"hermes kanban create {shlex.quote('中书省：能力增强機制')} --assignee planner --body '...' --json"
# ✅ Reliable
cmd = f"hermes kanban create capability-enhance-v0.7 --assignee planner --body '中书省：能力增强機制 v0.7 ...' --json"
```

**`kanban link` takes positional args, not flags.** The CLI syntax is `hermes kanban link <parent_id> <child_id>` — no `--parent`/`--child` flags:
```bash
# ✅ Correct
hermes kanban link t_parent t_child
# ❌ Wrong
hermes kanban link --parent t_parent --child t_child
```

**No `kanban remove` command.** To clean up test/accidental tasks, use `kanban archive` instead. There is no `remove`/`delete` subcommand.

**Fixing wrong dependency chains.** If you create T3/T4 with `--parent T1` but they should be `T1→T2→T3→T4`, use `unlink` then `link`:
```bash
hermes kanban unlink t_old_parent t_child   # remove wrong link
hermes kanban link t_new_parent t_child     # add correct link
```
This is safe while tasks are still `todo` — no dispatcher race.

**`--parent` with comma-separated IDs silently fails.** When a task needs multiple parents, passing `--parent t_aaa,t_bbb,t_ccc` to `kanban create` produces **empty JSON output** (no error message, no id returned). The workaround: create the task without `--parent`, then link each parent individually:
```bash
# ❌ Silent failure — returns empty JSON
hermes kanban create "multi-parent-task" --assignee engineer --parent t_aaa,t_bbb,t_ccc --json

# ✅ Create without parent, then link
hermes kanban create "multi-parent-task" --assignee engineer --json  # → returns id
hermes kanban link t_aaa <id>
hermes kanban link t_bbb <id>
hermes kanban link t_ccc <id>
```
When calling from Python with `json.loads()`, the empty output causes `JSONDecodeError`. Always check the raw output before parsing when `--parent` is involved.

## Orchestrator audit responsibility

When workers produce outputs that the orchestrator reports to the user, **spot-check key factual claims** before presenting them as truth. Workers run on models that hallucinate, and reviewer profiles may miss errors. In this session, a planner claimed DeepSeek V4-Pro had "幻觉率仅 4%" when the actual figure is 94%, and claimed Claude Code was unauthenticated when it was. The reviewer approved both times without catching either error.

The orchestrator is the last human-facing gate. For research/synthesis tasks especially, verify one or two critical numbers against the source data before the final report. Don't re-audit everything — that defeats the purpose of delegation. But catch the kind of error that would make the user doubt the whole result.

This is not a full御史台 audit — that's what the auditor profile is for. It's a sanity check on the numbers the user will actually read.

## Recovering stuck workers

When a worker profile keeps crashing, hallucinating, or getting blocked by its own mistakes (usually: wrong model, missing skill, broken credential), the kanban dashboard flags the task with a ⚠ badge and opens a **Recovery** section in the drawer. Three primary actions:

1. **Reclaim** (or `hermes kanban reclaim <task_id>`) — abort the running worker immediately and reset the task to `ready`. The existing claim TTL is ~15 min; this is the fast path out.
2. **Reassign** (or `hermes kanban reassign <task_id> <new-profile> --reclaim`) — switch the task to a different profile (one that exists on this setup) and let the dispatcher pick it up with a fresh worker.
3. **Change profile model** — the dashboard prints a copy-paste hint for `hermes -p <profile> model` since profile config lives on disk; edit it in a terminal, then Reclaim to retry with the new model.

**Rate-limit crashes are a special case.** If the crash log shows `RateLimitError`, `HTTP 429`, or `usage limit reached`, the worker itself cannot recover — the profile's provider/model is out of quota. The orchestrator (or operator) must switch the profile to a different model/provider before reclaiming. Do not reclaim blindly; the next worker will hit the same wall.

**Reclaim vs unblock for blocked tasks.** A task can be `blocked` for several different reasons:
- **Worker blocked it intentionally for a substantive gate** (e.g. `review-required: verdict=reject`, `needs-human-decision`, `security-risk`). Do **not** blindly unblock/retry. Read the block reason and comments/workspace first. For a reviewer rejection, spawn a new revision task that explicitly addresses the blockers, then a new/child review task; keep the original blocked review as the audit trail.
- **Worker blocked it intentionally for missing context or a user decision.** Ask/resolve the missing decision, then use `hermes kanban unblock <id>` to promote back to `ready`.
- **Dispatcher auto-blocked after crashes** (e.g. `consecutive_crashes=2`, rate limit exhausted, protocol violation). `reclaim` will fail with "not running or unknown id". Fix root cause if needed, then `unblock` + `dispatch`.
- **Config/credential mismatch crashes** (wrong provider, empty API key). The worker crashes immediately, dispatcher auto-blocks. Fix the root cause (see `references/provider-credential-pool-mismatch.md`), then `unblock` + `dispatch` or `reclaim` if the task is still running.

**Do NOT change model config without diagnosing the root cause.** (See `references/oaipro-claude-kanban-format.md` for a real case: oaipro + claude-opus-4-7 crashed in Kanban context but passed isolation test — premature model switch wasted time and broke intended config.) When a Kanban worker crashes, resist the urge to immediately switch profiles/models. The crash could be a transient message-format issue (e.g., an Anthropic-format content block hitting an OpenAI-compatible endpoint mid-conversation), a rate-limit, or a context-specific edge case — not a config error. **Test in isolation first**: run `hermes -p <profile> chat -q "simple test" --yolo`. If the simple query works, the config is correct and the crash context needs deeper diagnosis. The Emperor explicitly corrected a premature model switch in a live session — the config was fine, the crash was a Kanban-context-specific format conflict. Changing the config wasted time and broke the intentionally-chosen model stack.

**Reviewer `review-required` pitfall.** In 三省六部 flows, `review-required` can mean either (a) the worker self-blocked incorrectly after finishing work, or (b) 门下省 formally rejected a draft. Distinguish by reading `Latest summary`, `Events`, and comments/workspace. If it contains `verdict=reject` and specific blockers, treat it as a valid gate decision and route a revision chain; do not call it a process failure.

**Revision chain parent trap.** When a reviewer blocks with `verdict=reject`, the next step is a revision task. Do NOT set the revision task's `--parent` to the blocked reviewer — a blocked parent's children will never promote (blocked ≠ done). Create the revision as an independent task with no parent. The original blocked reviewer remains as audit trail. Example:

```bash
# ❌ WRONG — revision never promotes because parent is blocked
hermes kanban create "revise" --assignee planner --parent t_blocked_reviewer ...

# ✅ CORRECT — revision runs immediately
hermes kanban create "revise" --assignee planner ...  # no --parent

# Then chain: revise → new reviewer → auditor → archivist
hermes kanban create "rereview" --assignee reviewer --parent t_revise ...
```

**Double-parent blocking trap (NEW — 2026-05-19).** When you replace a rejected review with a new review, the downstream implementation task ends up with TWO parents: the old blocked reviewer AND the new approved reviewer. One blocked parent = whole task stuck in `todo` forever. ALWAYS inspect `parents` with `hermes kanban show <child> --json`, then unlink every superseded or blocked review parent:

```bash
# After creating revise → rereview chain and linking rereview to implement:
hermes kanban show t_implement --json        # verify actual parents
hermes kanban unlink t_blocked_old_reviewer t_implement  # remove the bad parent
hermes kanban dispatch  # now implement has only the done rereview parent → promotes
```

If `unlink` reports "No such link" but the child still shows a blocked parent, re-run `show --json` and remove the *current* parent ID; coordinator/recovery chains may have already rewired the child to a newer blocked review. Do not archive a blocked review before confirming it is no longer a parent of the execution/audit card.

**Worker self-block with stale task references (NEW — 2026-05-19).** Workers may complete their work but self-block citing task IDs from EARLIER chains that have already been archived (e.g., 将作监 self-blocks with "待御史终审(t_7fc710b4)" when t_7fc710b4 was archived 3 revision chains ago). The work is done, the reference is stale. Recovery: `unblock` → `complete` (force-complete). Do NOT spawn a new worker — the work was finished.

Hallucination warnings appear on tasks where a worker's `kanban_complete(created_cards=[...])` claim included card ids that don't exist or weren't created by the worker's profile (the gate blocks the completion), or where the free-form summary references `t_<hex>` ids that don't resolve (advisory prose scan, non-blocking). Both produce audit events that persist even after recovery actions — the trail stays for debugging.

**`kanban show --json` returns nested structure, not flat.** The output is `{task: {id, status, ...}, runs: [...], latest_summary: "..."}`. Access task fields via `data['task']['status']`, NOT `data['status']`. The runs array and latest_summary are siblings of `task`, not children of it:

```python
# ❌ Wrong — returns None
d = json.loads(output)
status = d['status']

# ✅ Correct
status = d['task']['status']
summary = d.get('latest_summary', '')
for run in d.get('runs', []):
    print(run['summary'])
```

**`kanban list --json` on large boards (300+ tasks) may contain control chars.** Task bodies with multiline content or Unicode can produce JSON with embedded control characters. `json.loads()` fails with `JSONDecodeError: Invalid control character`. Fix: `json.loads(raw, strict=False)`.

**`execute_code` + nested f-string + triple-quote = SyntaxError.** The sandbox Python doesn't handle `shlex.quote('''...''')` inside an f-string inside `execute_code`. This produces `SyntaxError: unterminated string literal`. Workaround: write the body to a temp file (`write_file`), then use `$(cat /tmp/file)` in the terminal command, or use escaped quotes.

**Bulk archiving old done tasks.** When the board has hundreds of stale `done` tasks (>7 days old), archive them in batches of 50–100 via Python subprocess:

```python
import subprocess, json
items = json.loads(sys.stdin.read(), strict=False)
done = sorted([t for t in items if t['status']=='done'], key=lambda t: t['created_at'])
batch = [t['id'] for t in done[:100]]
for tid in batch:
    subprocess.run(['hermes','-p','regent','kanban','archive',tid], timeout=15)
```

**`no_agent=true` cron jobs (watchdog, coordinator) do NOT use any LLM model.** They are pure Python scripts — `model`/`provider` fields are null and don't need switching. Rate-limit errors in the conversation come from the main Regent session, not from these scripts.

**`execute_code` + `~` sandbox home redirect (NEW — 2026-05-25).** `execute_code` runs in a sandbox where `~` and `$HOME` are redirected to the profile sandbox home (e.g. `~/.hermes/profiles/regent/home/`), NOT the real user home (`~/`). When checking whether an engineer task actually deployed files, do NOT use `execute_code` — any `os.listdir(os.path.expanduser("~/.hermes/profiles/shangshu"))` reads the sandbox. Use `terminal` with absolute paths instead: `ls ~/.hermes/profiles/shangshu/`. If an engineer claims files were created but `ls ~/.hermes/profiles/shangshu/` returns empty, suspect sandbox redirect before concluding the deploy failed. This pitfall caused a false "deployment not found" alarm during 尚书省 Phase 1 verification.

**Kanban auto-recovery chain validation (NEW — 2026-05-25).** The vNext coordinator auto-creation of revision chains was validated: when reviewer blocked with `verdict=reject`, the coordinator created `中书补正 → 门下复审` and rewired the downstream auditor from the blocked reviewer to the new reviewer. This happened fully automatically. When inspecting a blocked reviewer, always check for auto-created revision cards before manually building a recovery chain. The pattern: read the block comment → if it includes `【协调处置】`, the coordinator has already built the revision chain and the Regent just needs to wait for it to complete.
## ✅ Verification Checklist (RUN BEFORE CREATING KANBAN CHAINS)

- [ ] Did I discover available profiles before planning (Step 0)?
- [ ] Did I sketch the task graph out loud to the user before creating cards?
- [ ] Did I insert 尚书省 in the execution chain (planner→reviewer→SHANGSHU→...)?
- [ ] Did I verify parent dependencies are real data dependencies (not just "and also check X")?
- [ ] Did I set up proactive monitoring (60-90s polling, not waiting for user to ask "进度?")?

**If any box is unchecked, go back.**
