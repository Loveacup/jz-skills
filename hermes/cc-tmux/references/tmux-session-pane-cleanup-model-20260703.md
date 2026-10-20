# tmux Session/Pane Cleanup Model — 2026-07-03 incident lesson

## Trigger

User corrected Hermes during CC/tmux cleanup: the right unit was **tmux session**, not tmux server/process. A mistaken `ps | grep claude` cleanup matched the tmux server argv because the server command line retained `claude --model ...`, killing the server and all sessions. tmux-continuum then restored many old sessions because auto-restore was enabled.

## Evidence from the session

- `tmux kill-session -t <session>` is the safe session-level cleanup primitive.
- `tmux kill-server` destroys the server and all sessions; it is not a cleanup primitive.
- `tmux server -> session -> window -> pane -> process/pty`; CC execution state is not identical to any one tmux layer.
- `~/.tmux.conf` had:
  - `@resurrect-processes 'claude'`
  - `@continuum-restore 'on'`
  - `@continuum-save-interval '15'`
- tmux-continuum restores on tmux server start; `~/tmux_no_auto_restore` disables auto restore for the next server start.
- Existing cc-tmux scripts only enumerate `hermes-cc-*`; resurrected/manual/numeric sessions with Claude panes can be missed.
- `tmux -F '#{session_name}\t#{session_attached}'` produced literal `\t` in practice; use `|` or another explicit delimiter and parse accordingly.

## Correct mental model

| Layer | Meaning | Cleanup stance |
|---|---|---|
| tmux server | owns all sessions/clients/windows/panes | never kill by default |
| tmux session | main isolation/cleanup container | preferred cleanup unit after confirmation |
| tmux window | sub-container inside session | not default cc-tmux cleanup unit |
| tmux pane | PTY/process container | only targeted/manual cleanup |
| process | `claude`, shell, mcp child, etc. | kill only confirmed orphan; never broad argv grep |
| Claude Code session/history | CC internal state under `~/.claude` | never delete for tmux cleanup |

## Safe cleanup taxonomy

1. **Discovery first**: `tmux list-sessions` + `tmux list-panes -a` before any destructive command.
2. **Default preserve attached**: attached sessions are protected unless user explicitly names them.
3. **Session-level cleanup**: kill stale/detached session with `tmux kill-session -t <exact-session>`.
4. **No server kill**: `tmux kill-server` is dangerous and requires explicit “destroy the whole tmux server” wording.
5. **No broad process kill**: never use `ps | grep claude` to derive kill targets; tmux server argv may include `claude`.
6. **Resurrect awareness**: if continuum/resurrect is active, explain that killed sessions may reappear on server restart unless restore is disabled or the saved snapshot is updated.

## Classification matrix for future doctor/gc work

| Class | Signal | Default action |
|---|---|---|
| `managed` | `hermes-cc-*` or cc lock/status/heartbeat evidence | cc-gc/cc-finish path |
| `suspected` | non-managed pane command/title/capture looks like Claude | report only; manual review |
| `attached` | `session_attached=1` | protect by default |
| `external` | no CC evidence | ignore |
| `orphan-state` | `/tmp/cc-*` state references dead session | safe for `cc-gc --apply` orphan cleanup only |

## Proposed script direction

- Extend `cc-active-sessions.sh` or add a read-only `cc-tmux-doctor` that inventories **all** sessions/panes and classifies `managed/suspected/attached/external`.
- Keep `cc-gc.sh --apply` limited to orphan state cleanup. Do not make it kill live sessions.
- If a cleanup command is later added, require single-target confirmation: `--kill-session <name> --confirm <name>`.
- Doctor should detect `@continuum-restore`, `@continuum-save-interval`, `@resurrect-processes`, and `~/tmux_no_auto_restore`, but must not silently modify `~/.tmux.conf`.

## Regression tests to add if implementing scripts

- Attached session is never in apply candidates.
- Detached `hermes-cc-*` stale session is reported as managed candidate.
- Numeric/manual session with Claude pane is reported as suspected, not auto-killable.
- No normal cleanup path invokes `kill-server`.
- Delimiter parsing does not rely on literal `\t`.
- Continuum enabled state is reported as restore risk.
- Orphan `/tmp/cc-*` state cleanup does not kill live sessions.
