---

name: kanban-orchestrator
description: Decomposition playbook + anti-temptation rules for an orchestrator profile routing work through Kanban. The "don't do the work yourself" rule and the basic lifecycle are auto-injected into every kanban worker's system prompt; this skill is the deeper playbook when you're specifically playing the orchestrator role.
type: routine
version: 3.2.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing]
    related_skills: [kanban-worker]

---

# Kanban Orchestrator — Decomposition Playbook

> The **core worker lifecycle** (including the `kanban_create` fan-out pattern and the "decompose, don't execute" rule) is auto-injected into every kanban process via the `KANBAN_GUIDANCE` system-prompt block. This skill is the deeper playbook when you're an orchestrator profile whose whole job is routing.

## Profiles are user-configured — not a fixed roster

Hermes setups vary widely. Some users run a single profile that does everything; some run a small fleet (`docker-worker`, `cron-worker`); some run a curated specialist team they've named themselves. There is **no default specialist roster** — the orchestrator skill does not know what profiles exist on this machine.

Before fanning out, you must ground the decomposition in the profiles that actually exist. The dispatcher silently fails to spawn unknown assignee names — it doesn't autocorrect, doesn't suggest, doesn't fall back. So a card assigned to `researcher` on a setup that only has `docker-worker` just sits in `ready` forever.

**Step 0: discover available profiles before planning.**

Use one of these:

- `hermes profile list` — prints the table of profiles configured on this machine. Run it through your terminal tool if you have one; otherwise ask the user.
- `kanban_list(assignee="<some-name>")` — sanity-check a single name. Returns an empty list (rather than an error) for an unknown assignee, so this only confirms a name you're already considering.
- **Just ask the user.** "What profiles do you have set up?" is a fine first turn when the goal needs more than one specialist.

Cache the result in your working memory for the rest of the conversation. Re-asking every turn wastes a tool call.

## When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:

1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.

If *none* of those apply — it's a small one-shot reasoning task — use `delegate_task` instead or answer the user directly.

### Alex two-profile routing boundary

On Alex's default + regent setup, route by complexity and risk, not by a hard internal/external-agent split:

- **Xiao Huang / default handles directly or creates a simple card** when the work is ≤2 steps, single-lane, likely same-day closure, low risk, and has no strong review gate.
- **Regent / Taizi leads orchestration and creates the DAG** when the work is ≥3 steps, has true dependencies, needs a review gate, spans days or profiles, or touches system-critical configuration.
- **Gray zone:** Xiao Huang does the first clarification and task slicing. If dependencies or risk cross the threshold, escalate to Regent with a self-contained handoff: background, goal, constraints, acceptance criteria, and known risks.

### Model-level routing — cheap/strong dual-core

Parasitic on the D3 complexity routing above, lane execution model selection follows a cheap-default rule:

- **Cheap lane pool (default for chores):** CC Sonnet (`claude-sonnet-4`) + Codex Spark (`gpt-5.3-codex-spark`). Used for mechanical tasks: frontmatter fixes, tag normalization, template filling, simple file ops, bounded single-file edits.
- **Strong lane pool (override for heavy work):** CC Opus/Fable + Codex GPT-5.5. Used for architecture, review, multi-file refactors, security-sensitive changes.
- **Override mechanism:** Kanban card `metadata.model` field — `cheap` (default), `strong`, or a specific model ID. Cards without the field default to `cheap`.
- **L0 machine checks:** All cheap-lane output must pass schema validation + git diff scope check + naked tag scan before human review. Any failure → auto-block.
- **L2 spot-check:** Regent spot-checks cheap-lane output as part of existing review gates.

Full spec: `references/lane-model-routing.md`. Card template: `templates/cheap-lane-card.md`.

## The anti-temptation rules

Your job description says "route, don't execute." The rules that enforce that:

- **Do not execute the work yourself.** Your restricted toolset usually doesn't even include terminal/file/code/web for implementation. If you find yourself "just fixing this quickly" — stop and create a task for the right specialist.
- **For any concrete task, create a Kanban task and assign it.** Every single time.
- **Split multi-lane requests before creating cards.** A user prompt can contain several independent workstreams. Extract those lanes first, then create one card per lane instead of bundling unrelated work into a single implementer card.
- **Run independent lanes in parallel.** If two cards do not need each other's output, leave them unlinked so the dispatcher can fan them out. Link only true data dependencies.
- **Never create dependent work as independent ready cards.** If a card must wait for another card, pass `parents=[...]` in the original `kanban_create` call. Do not create it first and link it later, and do not rely on prose like "wait for T1" inside the body.
- **If no specialist fits the available profiles, ask the user which profile to create or which existing profile to use.** Do not invent profile names; the dispatcher will silently drop unknown assignees.
- **Decompose, route, and summarize — that's the whole job.**

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

### Step 5 — Report back to the user

Tell them what you created in plain prose, naming the actual profiles you used:

> I've queued 4 tasks:
> - **T1** (`<profile-A>`): cost comparison
> - **T2** (`<profile-A>`): performance comparison, in parallel with T1
> - **T3** (`<profile-B>`): synthesizes T1 + T2 into a recommendation
> - **T4** (`<profile-C>`): turns T3 into a CTO memo
>
> The dispatcher will pick up T1 and T2 now. T3 starts when both finish. You'll get a gateway ping when T4 completes. Use the dashboard or `hermes kanban tail <id>` to follow along.

## Common patterns

**Fan-out + fan-in (research → synthesize):** N research-style cards with no parents, one synthesis card with all of them as parents.

**Parallel implementation + validation:** one implementer card makes the change while one explorer/researcher card verifies config, docs, or source mapping. A reviewer card can depend on both. Do not make the implementer own unrelated verification just because the user mentioned both in one sentence.

**Pipeline with gates:** `planner → implementer → reviewer`. Each stage's `parents=[previous_task]`. Reviewer blocks or completes; if reviewer blocks, the operator unblocks with feedback and respawns.

**Same-profile queue:** N tasks, all assigned to the same profile, no dependencies between them. Dispatcher serializes — that profile processes them in priority order, accumulating experience in its own memory.

**Human-in-the-loop:** Any task can `kanban_block()` to wait for input. Dispatcher respawns after `/unblock`. The comment thread carries the full context.

### Review card creation (Alex two-profile setup)

When creating a review child card for regent on Alex's setup, include the mandatory adversarial prompt and parent timeout:

```python
import time

review_card = kanban_create(
    title="Review: <implementation card title>",
    assignee="regent",
    parents=[implementation_task_id],
    body="Review checklist per cc-lane-dual-substrate-template: ...",
    metadata={
        "review": {
            "adversarial_prompt": (
                "Before approving, list 3 specific ways this change could "
                "fail or be wrong, then explain why each is inapplicable or mitigated."
            ),
            "heterogeneous_gate": {
                "required": False,  # set True for critical config/security changes
            }
        },
        "parent_timeout_at": int(time.time()) + 3600,  # 1h default
    },
    max_runtime="20m",
    skills=["claude-code", "kanban-orchestrator"],
)
```

Key rules:
- `metadata.review.adversarial_prompt` is **mandatory** on Alex's setup — regent must respond to it before passing
- `metadata.parent_timeout_at` is **mandatory** for any card with `parents` — prevents infinite wait on silently-exited workers
- Before setting `skills=[...]`, verify the assignee profile can actually see those skills (`hermes -p <assignee> skills list` when available). If a review profile cannot see `claude-code`, `kanban-orchestrator`, or the domain skill, either fix visibility first or make the card body self-contained and omit nonessential skills. A crash with `Unknown skill(s)` is a routing/config failure, not an artifact verdict.
- For changes touching system-critical config, security boundaries, or lane infrastructure, set `heterogeneous_gate.required = True` to force MoA or external-model secondary verification
- See `references/adversarial-review-gate.md`, `references/sqlite-resilience-kit.md`, and `references/cross-substrate-audit-review-loop.md` for full details

## Related References

- `references/kanban-modes-overview.md` — Five Kanban modes decision tree (single-task, swarm, orchestrator, triage, goal). Load when choosing which mode fits the task.
- `references/kanban-swarm-setup.md` — Swarm profile creation: port config, Telegram disable, model assignment, gateway startup, dispatch patterns (2026-06-04 verified)
- `references/model-pinning-stable-artifacts.md` — Model-pinning all collaborating agents, gateway reload, and stable final-artifact workspace handoff for file/PDF/audio deliverables
- `references/kanban-modes-overview.md` — All five Kanban modes (single-task, swarm, orchestrator, triage, goal) with decision tree and CLI quick reference (2026-06-04)
- `references/kanban-ghost-task-investigation.md` — Investigation checklist for tasks that completed with `result_len=0, summary=None`: systematic search across profiles, session DBs, workspaces, logs, and audit trail. Use when a user asks "what did this task actually do?" and the completion has no trace.
- `references/cccmux-lane-smoke-pattern.md` — CC/cmux lane smoke-test pattern: visible `📡` progress, real intervention, disk verification, Final Input-Line Gate, and `metadata.cc_lane` handoff. Load before creating or reviewing a Kanban card that validates CC/cmux as a lane.
- `references/cc-lane-dual-substrate-template.md` — CC lane family template: shared contract plus `claude-code/tmux` adapter and `cccmux/cmux` adapter. Load before creating real CC lane cards or turning smoke patterns into reusable templates.
- `references/supervision-watchdog.md` — Out-of-band intervention bridge: dual-signal delivery (watchdog cronjob + file track) that survives worker self-trapping. Load when setting up supervision loops for long-running CC/tmux or cmux lane cards.
- `references/adversarial-review-gate.md` — Producer≠reviewer enforcement: adversarial prompt field (always-on) + heterogeneous verification gate (for critical changes). Load when creating review child cards — especially for implementation cards that touch system-critical config or lane infrastructure.
- `references/phase2-mvp-pattern.md` — Phase 2 MVP pattern: transitioning from smoke tests to real vault tasks, two-card structure (implementation + adversarial review), substrate selection for real work, value-acceptance criteria, anti-patterns, and D19 evidence. Load when planning the first real Kanban + CC lane task after smoke validation completes.
- `references/cross-substrate-audit-review-loop.md` — Cross-substrate production audit pattern: implementation on one substrate, adversarial review on another, request-changes follow-up, scope-fork checks, parser/category false-confidence checks, and assignee skill-visibility preflight. Load when creating or reviewing real audit/documentation cards across `cccmux/cmux`, `claude-code/tmux`, or direct Hermes execution.

## Pitfalls

**Inventing profile names that don't exist.** The dispatcher silently fails to spawn unknown assignees — the card just sits in `ready` forever. Always assign to a profile from your Step 0 discovery; ask the user if you're unsure.

**Bundling independent lanes into one card.** If the user asks for two independent outcomes, create two cards. Example: "fix blockers and check model variants" is not one fixer task; create a fixer/engineer card for the fixes and an explorer/researcher card for the variant check, then optionally gate review on both.

**Over-linking because of wording.** "Finally check X" may still be parallel with implementation if X is static config, docs, or source discovery. Link it after implementation only when the check depends on the implementation result.

**Forgetting dependency links.** If the task graph says `research -> implement -> review`, do not create all tasks as independent ready cards. Use parent links so implement/review cannot run before their inputs exist.

**Blocking a parent as `review-required` while the reviewer is a child card.** A child card cannot be claimed while its parent is not done; even a forced promote will be rejected with `parents_not_done`. If review is modeled as a child card, mark the implementation parent `done` with a summary like `implementation-ready-for-review` and let the child review card make the final pass/request-changes/reject decision. Use `block(review-required)` only when the same card itself is waiting for human input or when no child dependency is expected.

**Treating CC/cmux smoke as "file exists".** CC/cmux lane validation must prove the control plane, not just artifact creation. Require a running `📡` status comment/message, one real intervention/control action, disk readback, Final Input-Line Gate handling, and `metadata.cc_lane`. See `references/cccmux-lane-smoke-pattern.md`.

**Treating cccmux as the replacement for claude-code/tmux.** Alex is comparing both substrates in parallel. For CC lane cards, explicitly choose `claude-code/tmux` or `cccmux/cmux`, state why, and use the corresponding adapter in `references/cc-lane-dual-substrate-template.md`.

**Creating review cards without checking assignee skill visibility.** A child card can be syntactically valid but crash immediately if the assignee profile cannot see the named `skills` (`Unknown skill(s): ...`). Before dispatching a review card with explicit `skills=[...]`, verify visibility from the assignee profile or omit nonessential skills and make the body self-contained. If such a crash happens, treat it as routing/config debt and continue only after recording the weakened review conditions.

**Using `~` in cross-profile `skills.external_dirs`.** Dispatcher-spawned workers may run with subtly different home/profile context than an interactive shell. If a profile relies on shared skills, prefer an absolute external dir such as `/Users/<user>/.hermes/skills` over `~/.hermes/skills`, then verify with a real Kanban card that force-loads the required skills. Case: regent review initially crashed with `Unknown skill(s): claude-code, kanban-orchestrator, obsidian`; changing `skills.external_dirs` to `/Users/alexcai/.hermes/skills` and dispatching verification card `t_9c6f534c` passed.

**Creating review cards without adversarial prompts.** Review child cards on Alex's setup must include `metadata.review.adversarial_prompt` — a mandatory counterfactual question the reviewer must answer before passing. Without it, regent review is susceptible to confirmation bias (same model family, same skill repo, same card payload). See `references/adversarial-review-gate.md`.

**Relying solely on in-loop supervision polling for long-running CC lane tasks.** When a CC worker is stuck in a multi-minute tool call, it never reaches the `kanban_show` polling point. For CC lane cards with expected runtime >5min, consider adding a `no_agent=True` watchdog cronjob that writes interventions to `/tmp/kanban-intervene-{task_id}.md` — decoupled from worker liveness. See `references/supervision-watchdog.md`.

**Creating cards with parents but no timeout.** Every card with `parents` should include `metadata.parent_timeout_at` (Unix timestamp). Without it, child cards can wait forever for a parent that silently exited without completing. See `references/sqlite-resilience-kit.md`.

**Reassignment vs. new task.** If a reviewer blocks with "needs changes," create a NEW task linked from the reviewer's task — don't re-run the same task with a stern look. The new task is assigned to the original implementer profile.

**Argument order for links.** `kanban_link(parent_id=..., child_id=...)` — parent first. Mixing them up demotes the wrong task to `todo`.

**Don't pre-create the whole graph if the shape depends on intermediate findings.** If T3's structure depends on what T1 and T2 find, let T3 exist as a "synthesize findings" task whose own first step is to read parent handoffs and plan the rest. Orchestrators can spawn orchestrators.

**Launching swarm without reading the setup docs.** Swarm requires one gateway per worker profile, each on a unique port. Don't assume you can just `hermes profile create` and go — read `references/kanban-swarm-setup.md` first. Port conflicts, Telegram token collisions, and model assignment are all footguns that the setup doc covers.

**User-specified model only set on root profile.** If the user says all collaborating agents must use a model, update every participating profile's `model.default` and `fallback_providers`, then restart/kickstart gateways before dispatch. Setting only the orchestrator/root profile lets workers fall back to stale models.

**Final artifacts left in scratch workspace.** Scratch kanban workspaces can disappear after completion. For user-facing files, use a stable `dir:` workspace on the finalizer or immediately persist/regenerate artifacts under the active profile workspace before reporting completion.

**Tenant inheritance.** If `HERMES_TENANT` is set in your env, pass `tenant=os.environ.get("HERMES_TENANT")` on every `kanban_create` call so child tasks stay in the same namespace.

**Routing rules belong in this skill, not memory.** If a planning session decides reusable Kanban boundaries (who routes, who reviews, when to escalate, which lane gets failure control), patch `kanban-orchestrator` or the lane skill. Do not leave those as user/profile memory or Supermemory facts; memory is too sticky and becomes stale operating policy.

## Smoke-testing / dry-run caveats

When validating Kanban modes, do not assume a new board is an execution sandbox. Gateway dispatchers can scan newly-created boards and automatically claim any `ready` cards, even if you intended to test only CLI graph creation. For smoke tests that should not run workers, prefer `--initial-status blocked`, create dependency-gated `todo` cards, temporarily stop/disable dispatchers, or immediately `reclaim` + `block` any cards the gateway claims.

Additional smoke-test gotchas:
- `decompose` is not a dry-run. It can create real child tasks, and those children may become runnable.
- `block` does not directly block `todo` tasks; use dependency-gated `todo` as inert evidence, or `promote` then `block`/`archive` if cleanup requires a non-todo state.
- After accidental auto-claim, run `hermes kanban reclaim <task_id>` and verify no `work kanban task <task_id>` processes remain before reporting cleanup.

## Goal-mode cards (persistent workers)

By default a dispatched worker gets **one shot** at its card: it does its work, calls `kanban_complete`/`kanban_block`, and exits. For open-ended cards where one turn rarely finishes the job, pass `goal_mode=True` to wrap that worker in a Ralph-style goal loop — the same engine behind the `/goal` slash command:

```python
kanban_create(
    title="Translate the full docs site to French",
    body="Acceptance: every page translated, no English left, links intact.",
    assignee="<translator-profile>",
    goal_mode=True,        # judge re-checks the card after each turn
    goal_max_turns=15,     # optional budget (default 20)
)["task_id"]
```

How it behaves:
- After each worker turn, an auxiliary judge evaluates the worker's response against the card's **title + body** (treated as the acceptance criteria).
- Not done + budget remains → the worker keeps going **in the same session** (full context retained — not a fresh respawn).
- Worker calls `kanban_complete`/`kanban_block` itself → loop stops, normal lifecycle.
- Budget exhausted without completion → the card is **blocked** for human review (sticky), never a silent exit.

When to use it: long, multi-step, or "keep going until X is true" cards. When NOT to: cheap one-shot cards (translation of a single string, a quick lookup) — the judge overhead isn't worth it, and the dispatcher's existing retry/circuit-breaker already handles transient worker failures.

Write the body as **explicit acceptance criteria** — the judge is only as good as the goal text. "Translate the README" is weaker than "Translate every section of the README to French; no English sentences remain."

## Recovering stuck workers

When a worker profile keeps crashing, hallucinating, or getting blocked by its own mistakes (usually: wrong model, missing skill, broken credential), the kanban dashboard flags the task with a ⚠ badge and opens a **Recovery** section in the drawer. Three primary actions:

1. **Reclaim** (or `hermes kanban reclaim <task_id>`) — abort the running worker immediately and reset the task to `ready`. The existing claim TTL is ~15 min; this is the fast path out.
2. **Reassign** (or `hermes kanban reassign <task_id> <new-profile> --reclaim`) — switch the task to a different profile (one that exists on this setup) and let the dispatcher pick it up with a fresh worker.
3. **Change profile model** — the dashboard prints a copy-paste hint for `hermes -p <profile> model` since profile config lives on disk; edit it in a terminal, then Reclaim to retry with the new model.

Hallucination warnings appear on tasks where a worker's `kanban_complete(created_cards=[...])` claim included card ids that don't exist or weren't created by the worker's profile (the gate blocks the completion), or where the free-form summary references `t_<hex>` ids that don't resolve (advisory prose scan, non-blocking). Both produce audit events that persist even after recovery actions — the trail stays for debugging.

**Ghost tasks (completed with no trace):** A worker may call `kanban_complete()` with `result_len=0, summary=None` — the task is marked done but left no session, no workspace, no log, and no audit trail. See `references/kanban-ghost-task-investigation.md` for the full investigation checklist (cross-profile session search, workspace check, audit log scan).
