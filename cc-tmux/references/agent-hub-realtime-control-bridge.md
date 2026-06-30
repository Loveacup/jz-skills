# Agent-hub realtime CC control bridge pattern (2026-06-25)

Use when building a hub/worker layer above cc-tmux (iii/NATS/Hermes or similar) that must let Hermes monitor and intervene in CC sessions in real time. This is not a replacement for cc-tmux; it is the bridge pattern for exposing cc-tmux safely to another runtime.

## Core contract

- **Monitor before intervene**: never blind-send corrective instructions. `intervene` must either require a recent `monitor_snapshot_id` or automatically run monitor first and include `monitor_before`/`monitor_after` in the result.
- **Sent is not completed**: an execute/send return code only means the context was delivered. Return a lifecycle marker such as `sent_not_completed`; completion still requires turn-done/status/output verification.
- **Gated interrupt**: `interrupt` requires explicit `confirm:true` and a non-empty reason. Do not expose raw kill as a normal control action.
- **Event everything**: control calls should return synchronously *and* best-effort publish an event, e.g. `agent.cc.control.monitor`, `agent.cc.control.intervene`, `agent.cc.control.execute`.
- **Bound the watcher**: long-running monitoring should be a bounded loop with `max_ticks`/timeout and terminal-state exit, not an infinite loop or manual human polling.
- **Do not bypass cc-start safety**: if cc-start reports active sessions / needs `--ack-active`, surface `active_sessions_require_ack`; do not auto-confirm.

## VM-to-host bridge shape

When the worker runs in a VM/sandbox that cannot access host tmux directly:

```text
Hermes / iii worker VM
  -> HTTP token bridge on host (/control, /healthz)
  -> cc-tmux scripts on host
  -> tmux / Claude Code session
```

Bridge requirements:

- `/healthz` must be available so Hermes can check bridge/token status before control calls.
- Token is mandatory by default; a no-token mode is only for local smoke tests.
- If the VM is rebuilt/restarted, reprovision the token into the VM before calling the bridge.
- The bridge should whitelist actions: `execute`, `monitor`, `intervene`, `interrupt`.

## Execute lifecycle

For a new CC task, make the lifecycle explicit:

```text
cc-start.sh -> cc-monitor.sh -> cc-send.sh -> cc-monitor.sh
```

The monitor-before-send check is not completion verification; it proves the session exists and gives a baseline. The monitor-after-send check proves delivery/initial state. The returned status should remain `sent_not_completed` until a later watcher/turn-done/output check proves completion.

## Persistent intervention context

A real smoke found that writing intervention text to a temporary directory and deleting it immediately breaks CC: `cc-send.sh` passes a file path, and CC may read it later. If the file is deleted before CC reads it, the intervention becomes a broken path.

Therefore intervention context must be written to a durable temp file, e.g.:

```text
/tmp/agent-hub-cc-intervention-<session>-<timestamp>.md
```

Return this `context_path` in the intervention result for auditability.

## NATS/event publishing pitfalls from VM workers

A VM worker's `127.0.0.1` is the VM, not the host. For host NATS, default to the VM-to-host gateway (in this setup `100.96.0.1:4222`) or make host/port explicit via env.

Always put a short publish timeout around best-effort events (e.g. 1500ms). Event publishing must never block real-time control; if it fails, return the control result with `event_published:false` and an error field.

## Bounded watcher pattern

Use a small watcher process when Hermes needs continuing visibility after dispatch:

```text
watcher process
  -> periodic iii trigger cc::monitor
  -> emit JSONL on first frame, state changes, and terminal states
  -> stop on COMPLETED/BLOCKED/FREEZE/error
  -> stop with timeout after max_ticks
```

Recommended event shape:

```json
{
  "kind": "cc.watch.event",
  "session_id": "hermes-cc-default-agent-hub-0625-1600",
  "sequence": 1,
  "state": "TOOL",
  "terminal": false,
  "monitor": { "kind": "cc.monitor", "status": "ok", "event_published": true }
}
```

Important details:

- Emit only the first frame, state changes, and terminal states to avoid spam.
- Treat `COMPLETED`, `BLOCKED`, `FREEZE`/`FROZEN`, and monitor `status:error` as terminal.
- On `max_ticks` exhaustion, emit a terminal timeout event and exit non-zero (e.g. 2). This is not a crash; it means the bounded observation window expired.
- The watcher is a visibility/control primitive. It should not kill sessions or auto-answer CC questions. Intervention decisions stay in Hermes/user policy unless explicitly designed otherwise.

## Stale-state intervention suggestions

A bounded watcher may detect that a session has stayed in the same non-terminal state for multiple ticks. Capture this as an **auditable suggestion**, not an automatic intervention:

```json
{
  "kind": "cc.intervention.suggestion",
  "reason": "state_stale",
  "state": "TOOL",
  "repeated_ticks": 8,
  "monitor_snapshot_id": "cc-monitor-...",
  "auto_execute": false,
  "message": "CC session ... is still TOOL after 8 watch ticks..."
}
```

Rules:

- `auto_execute` must be `false` by default. The watcher must not call `cc::intervene` on its own.
- Include the latest `monitor_snapshot_id` so a later intervention can satisfy monitor-before-intervene.
- Emit suggestions inside the normal `cc.watch.event` JSONL stream, so Hermes/user policy can decide whether to act.
- Do not suggest on terminal states (`COMPLETED`, `BLOCKED`, `FREEZE`/`FROZEN`) or monitor errors; those are completion/escalation paths, not semantic nudges.
- Suggested text should be concise and framed as “consider sending a follow-up if unexpected,” not as an instruction to automatically nag CC.

## Smoke sequence that proved the loop

1. Start token bridge on host.
2. Restart worker VM and provision bridge token.
3. `cc::bridge_status` -> `status:ok`, `event_published:true`.
4. `cc::execute` -> `start -> monitor -> send -> monitor`, returns `sent_not_completed`.
5. Run a bounded watcher. It should output `cc.watch.event` JSONL and include the underlying monitor payload.
6. If CC is idle or misread the context, use `cc::intervene` with monitor evidence.
7. Verify CC consumed the persistent context and produced the expected output.
8. `cc-finish --release-lock`; do not kill session unless the user confirms.

## Key lesson

The user's requirement is not “dispatch CC tasks”; it is a **Hermes control loop**: monitor, detect drift, intervene, verify, and emit events so the system can keep watching without relying on human memory. The safe progression is: synchronous result for the immediate caller, NATS event for the system, bounded watcher for continuity, and human/Hermes policy for any semantic intervention.
