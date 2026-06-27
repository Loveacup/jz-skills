# Kanban CC/cmux Lane Smoke Pattern

Use this when validating a CC/cmux lane before trusting it for real work. The class of task is: a Kanban worker drives `cmux claude-teams` as a lane, while Kanban remains the lifecycle/audit layer.

## What the smoke must prove

A CC/cmux smoke does **not** pass just because CC writes a file. It must prove the control plane:

1. **Visible progress** — at least one `📡 cccmux Team` status block while the run is active. If the worker cannot message the user directly, it must write the status block to a Kanban comment during execution.
2. **Intervention** — at least one real control action, such as `cmux send` + `cmux send-key enter`, Feed handling, or workspace close. Describing that intervention is possible is not enough.
3. **Disk verification** — after Stop/idle, verify artifact path, size, and readback.
4. **Audit handoff** — write `metadata.cc_lane` and review evidence to Kanban.

## Occupancy and isolation rule

If occupancy scan reports a historical `needsInput` session, do not touch it unless explicitly authorized. Prefer a new isolated workspace/cwd for the smoke. Record in the card body that old sessions are forbidden scope.

Preflight:

```bash
bash ~/code/jz-skills/hermes/cccmux/references/occupancy-scan.sh
cmux ping
cmux tree --all
cmux top --processes
```

## Implementation card skeleton

Required fields:

- human authorization / occupancy policy;
- allowed temp cwd and output artifact path;
- forbidden actions: no skills/config/Obsidian/cron/gateway/Surge/Telegram/secrets;
- startup: create isolated cmux workspace + `cmux claude-teams --effort high`;
- events subscription with category filters;
- one user/Kanban-visible `📡 cccmux Team` status block;
- one intervention action;
- disk verification commands;
- Final Input-Line Gate;
- `metadata.cc_lane`.

## Final Input-Line Gate

After CC appears done, inspect the bottom prompt line before any close/continue action. If residual text remains (for example `show me the file` queued at the prompt), do **not** press Enter. Either clear it or close the isolated workspace. Record how the gate was handled in `metadata.cc_lane.verification.final_input_line_gate`.

This matters because a smoke run can otherwise accidentally execute a stale queued instruction after the artifact is already valid.

## Review child checklist

The reviewer should decide exactly one: `pass`, `request changes`, or `reject`.

Evidence to check:

- Were `📡` status blocks emitted during the run, not only in the final summary?
- Did the event log show relevant frames and seq range?
- Was intervention acknowledged by events or capture?
- Was the artifact read back from disk?
- Was the Final Input-Line Gate handled safely?
- Did the run avoid old sessions and forbidden paths?
- Is `metadata.cc_lane` complete enough for reuse?

## metadata.cc_lane minimum

```json
{
  "cc_lane": {
    "result": "accepted | partial | rejected | timed_out | interrupted",
    "status": "implementation-ready-for-review",
    "workspace": "workspace:<id>",
    "surface": "surface:<id>",
    "closed_after_completion": true,
    "events_subscription": {
      "ack_received": true,
      "log": "/absolute/path/cmux-events.ndjson",
      "seq_range": [0, 0],
      "event_counts": {}
    },
    "visible_status_comments": [],
    "intervention": {
      "action": "cmux send + cmux send-key enter",
      "text": "short/redacted instruction",
      "ack_events": []
    },
    "artifact": {
      "path": "/tmp/<dir>/result.md",
      "size_bytes": 0
    },
    "verification": {
      "cmux_ping": "PONG",
      "disk_verified": true,
      "readback_verified": true,
      "final_input_line_gate": "empty | clear | closed_workspace",
      "forbidden_paths_changed": false
    }
  }
}
```

## Example evidence from a passing smoke

A passing Phase 1.1 smoke had:

- Kanban implementation card: default worker, `done` as `implementation-ready-for-review`.
- Review card: regent, `pass`.
- Event log: 75 lines, seq range 600–676.
- Intervention: `surface.input_sent` + `surface.key_sent` acknowledged the steer.
- Artifact: `/tmp/.../result.md`, 454 bytes, exactly 3 bullets.
- Minor non-blocker: residual input line after completion; worker did not execute it and closed the isolated workspace.