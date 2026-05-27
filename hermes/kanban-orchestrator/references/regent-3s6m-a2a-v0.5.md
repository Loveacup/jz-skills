# Regent 3S6M A2A v0.5 — session reference

Session learning from the 三省六部 governance workflow on 2026-05-18.

## Artifacts produced

- Draft: `~/.hermes/kanban/workspaces/t_8e7dc55c/A2A-通信规范-v0.5.md`
- Revised after 门下省 rejection: `~/.hermes/kanban/workspaces/t_39332276/A2A-通信规范-v0.5-revised.md`
- Final after 御史台 non-blocking fixes: `~/.hermes/kanban/workspaces/t_2e8a4c28/A2A-通信规范-v0.5-final.md`
- Pending archive package: `~/.hermes/kanban/workspaces/t_b761ab8f/`

Do not treat these workspace paths as canonical docs forever; they are the handoff package for later Obsidian/skill archival.

## Final A2A decisions

- Default topology is star: `regent -> Kanban task graph -> specialist profiles`.
- Legal horizontal A2A has only two forms:
  1. **Kanban parent/child handoff** with valid `parent_id` and `child task_id`.
  2. **Regent-authorized bounded A2A request** with `task_id`, `timeout`, `budget`, `permissions`, and evidence.
- No task-id-less private chat between specialists.
- No post-hoc dependency linking when a child could race ahead; bind dependencies at task creation.
- Avoid horizontal context dumps. Keep handoffs compact and evidence-linked.

## Schema corrections that mattered

The 门下省 rejected the first draft for three blocking reasons:

1. Topology matrix contradicted the star-topology rule by allowing direct `planner -> reviewer` communication.
2. `correlation_id`, `permissions`, and `evidence` were insufficiently defined.
3. The word `review` conflated gate review, code review, and ordinary comments.

The accepted schema split these concepts:

- `gate_review`: 门下省封驳; lifecycle gate.
- `code_review`: code or implementation review; may be done by reviewer or 将作监.
- `comment`: ordinary non-gating note.

Evidence rules added in final:

- Use SHA-256 content hashes for referenced artifacts.
- Verify evidence chain before relying on a handoff.
- Evidence failure should produce explicit A2A errors such as `A2A-009` / `A2A-010`.

## Notification and rate controls

- Bounded A2A default limit: at most 3 horizontal requests per task.
- More requires regent approval.
- Respect the user's low-notification preference: notify only for blocked, high-risk, or final completion states.

## Workflow pitfall: self-blocking workers

Planner blocked a completed revision with `review-required`; engineer had a similar self-block pattern earlier. For 三省六部 workers:

- If the worker has produced the requested artifact, it should `kanban_complete`.
- Downstream review/audit tasks provide the gate; upstream workers must not block themselves waiting for review.
- Patch profile prompts if this recurs: “产出后即 kanban_complete，不主动 block 等待审查；审查由 Kanban 下游 reviewer 任务负责。”

## Archive discipline

The user explicitly said not to modify main-channel/Obsidian knowledge-base docs while another main-channel optimization was in progress. In that situation:

- Produce a待归档包 in a workspace.
- Do not overwrite Obsidian/notes docs.
- Later, when the main-channel docs are stable, merge the archive package rather than replacing the optimized docs.
