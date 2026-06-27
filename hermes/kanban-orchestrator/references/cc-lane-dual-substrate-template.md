# Kanban CC Lane Dual-Substrate Template

Use this when creating or reviewing a Kanban card that routes work to the **CC lane family**. CC lane is not a single backend. On Alex's setup it currently has two parallel substrates:

- `claude-code/tmux` — mature historical workflow: tmux interactive + Claude Code native agent team. Strong manual patrol discipline; progress is proven by `capture-pane` + user-visible `📡 CC Agent Team` blocks.
- `cccmux/cmux` — experimental/control-plane workflow: `cmux claude-teams`, cmux events, Feed decisions, workspace/surface isolation. Progress is proven by event subscription + user/Kanban-visible `📡 cccmux Team` blocks.

Do **not** describe `cccmux/cmux` as replacing `claude-code/tmux`. Pick a substrate per card and record the reason.

## Selection rule

Choose `claude-code/tmux` when:

- the task benefits from the known stable raw-tmux workflow;
- existing procedure/skill references are tmux-specific;
- you need the mature `capture-pane` patrol and Final Input-Line Gate discipline;
- cmux capability, Feed, or workspace/surface state is uncertain.

Choose `cccmux/cmux` when:

- the purpose is to validate or use cmux-native visibility/intervention;
- event stream / Feed / workspace control is materially useful;
- the card explicitly includes a control-plane acceptance criterion;
- a new isolated workspace/cwd is safe and cmux preflight passes.

If unclear, default to `claude-code/tmux` for real work and reserve `cccmux/cmux` for bounded smoke / pilot tasks until more evidence accumulates.

## Common CC lane contract

Every CC lane card, regardless of substrate, must include:

1. **Task scope** — goal, allowed paths, forbidden paths, and explicit non-goals.
2. **Substrate** — `metadata.cc_lane.substrate` is exactly `claude-code/tmux` or `cccmux/cmux`.
3. **Isolation** — independent session/workspace and independent cwd; no `--continue` unless explicitly authorized.
4. **Progress visibility** — status blocks during the run, not only in the final summary.
5. **Intervention boundary** — how user/regent can intervene and what the holder worker may do.
6. **Review gate** — implementation parent may complete as `implementation-ready-for-review`; review child decides `pass`, `request changes`, or `reject`.
7. **Disk verification** — artifact path, size, readback, and changed-path audit.
8. **Final Input-Line Gate** — inspect/clear/close safely before ending the CC session/workspace.
9. **Metadata handoff** — write `metadata.cc_lane` with evidence sufficient for regent review.

## tmux adapter

Required card fields for `claude-code/tmux`:

- skills: `claude-code`, `kanban-orchestrator` plus any domain skill;
- preflight: run `~/code/jz-skills/hermes/claude-code/references/occupancy-scan.sh` when available, or equivalent tmux session scan;
- launch: new `hermes-cc-{agent}-{ts}` tmux session, `HOME=/Users/alexcai`, `claude --model ... --effort high|xhigh|max`;
- progress: every `tmux capture-pane` is immediately paired with a user/Kanban-visible `📡 CC Agent Team` block;
- intervention: `tmux send-keys`, `C-c`, permission dialog handling, or handoff to user/regent;
- final gate: `tmux capture-pane -S -3 | tail -1` and never press Enter if residual text remains.

## cmux adapter

Required card fields for `cccmux/cmux`:

- skills: `cccmux`, `claude-code`, `kanban-orchestrator` plus any domain skill;
- preflight: `cmux ping`, `cmux tree --all`, `cmux top --processes`, and `cccmux` occupancy scan;
- launch: new isolated cmux workspace + cwd, then `cmux claude-teams --effort high|xhigh|max`;
- progress: persistent `cmux events` subscription plus at least one user/Kanban-visible `📡 cccmux Team` block while running;
- intervention: at least one lane-native action when validating the substrate (`cmux send`, `send-key`, Feed handling, capture, close workspace);
- final gate: capture bottom prompt line or close isolated workspace without executing residual input.

## metadata.cc_lane schema

```json
{
  "cc_lane": {
    "used": true,
    "substrate": "claude-code/tmux | cccmux/cmux",
    "substrate_reason": "why this substrate was selected",
    "status": "implementation-ready-for-review | pass | request_changes | reject | blocked",
    "result": "accepted | partial | rejected | timed_out | interrupted",
    "session": {
      "kind": "tmux | cmux",
      "id": "hermes-cc-... | workspace:<id>",
      "surfaces_or_panes": ["surface:<id> | %pane"]
    },
    "visibility": {
      "status_blocks_sent": 0,
      "first_status_target": "telegram | kanban_comment | both",
      "evidence_log": "/absolute/path/or kanban comment ids"
    },
    "interventions": [
      {
        "type": "observe | steer | unstick | interrupt | terminate",
        "source": "user | regent | worker",
        "action": "tmux send-keys | cmux send | Feed | close-workspace",
        "evidence": "short evidence summary or event/comment id"
      }
    ],
    "verification": {
      "disk_verified": true,
      "artifacts": ["/absolute/path"],
      "changed_paths": [],
      "final_input_line_gate": "empty | cleared | closed_workspace | killed_session",
      "forbidden_paths_changed": false
    }
  }
}
```

## Review child checklist

Reviewer checks:

- substrate matches card intent and is not falsely described as replacing the other substrate;
- required adapter-specific preflight evidence is present;
- progress was visible during execution;
- intervention path is demonstrated or explicitly not required for non-smoke real work;
- artifacts were read back from disk;
- Final Input-Line Gate was handled safely;
- parent completion means `implementation-ready-for-review`, not final acceptance.
