# Downstream project docs after cc-tmux skill updates (2026-06-25)

## Trigger

Use this when cc-tmux skill / cc-tmux OB docs changed in another topic and the user asks to update a dependent project such as agent-hub.

## Durable lesson

Do not treat cc-tmux as a static dependency. When cc-tmux gains new orchestration behavior, downstream project docs must update their **boundary language**, not just version numbers.

Example from agent-hub:

- cc-tmux v1.28 added R4c `delegate_task` checkpoint monitoring, user-progress-request priority, `cc-monitor` failure fallback to `tmux capture-pane`, path correction, and the rule that Hermes must not silently take over writing when the user explicitly delegated edits to CC.
- agent-hub docs previously framed itself as replacing/solving single-session monitoring. That became stale.
- Correct boundary: cc-tmux owns **single CC session bare-metal orchestration**; agent-hub owns **multi-session / multi-CLI / multi-machine registry, routing, lifecycle, and NATS event convergence**.

## Procedure

1. Load/read the current `cc-tmux` skill first; note version and newly added red lines.
2. Inspect the updated cc-tmux OB directory if the user mentions it changed: `20-Areas/20_技术项目/cc-tmux Skill 与 Agent 协作/`.
3. Search dependent project docs for stale assumptions:
   - old version numbers (`v1.26`, old assertion counts)
   - claims like `Hermes 自己 capture-pane`, `手动管理`, `文件散落`, `替代 marker`, `替代监控`
   - old alert/bridge mechanisms that conflict with the current architecture
4. Patch the dependent docs to express boundaries:
   - upstream skill owns the local/session protocol and its red lines
   - downstream project consumes or wraps that protocol without rewriting it
   - new red lines become constraints on future worker designs
5. Verify by searching for old wording and for new anchor terms.

## Pitfalls

- Do not simply paste the new skill changelog into downstream docs. Convert it into architectural consequences.
- Do not weaken upstream red lines. If cc-tmux says `monitor failure → fallback to tmux capture-pane`, downstream workers must implement that fallback or explicitly defer the requirement.
- Do not leave old contradictory Specs around as “warnings” once the architecture decision is settled. In the agent-hub session, `Phase 1 usage-worker Spec` still referenced `call("hermes-worker", "alert")`; after B2 was settled, the right fix was to replace it with NATS `agent.usage.alert` + a Hermes `delegate_task(background=true)` acceptance criterion.
- When the user complains about no progress/empty response, treat it as an immediate progress-reporting skill signal. In CC-driven OB edits, after any CC completion or follow-up send, read/verify outputs and reply with a status summary; never end the turn empty after tool calls.
