# cc-tmux driven-CC hooks (§3.3–3.7)

Source of truth for the L2 (CC-native) hook layer. All hooks sit on **non-deny
paths** (PostToolUse / Notification / SessionStart / Stop-block) and degrade
silently — if a hook never fires, the system falls back to L0/L1 behavior and
never wedges.

| File | Pitfall | Role |
|---|---|---|
| `cc-posttool.sh` | #8 | PostToolUse(Write\|Edit\|MultiEdit): best-effort format + archive >8KB artifacts to `/tmp/cc-output/<sess>/` |
| `settings.template.json` PostToolUse(Bash) | #8 | inline: archive >4KB `tool_response` to `/tmp/cc-output/<sess>/responses-*.log` |
| `settings.template.json` Notification | #4 | inline: append `{event:notification}` JSONL + touch heartbeat (mtime-only push) |
| `settings.template.json` SessionStart | #2 | inline: inject cc-tmux run-context + recent state tail on session/resume/compaction |
| `cc-stop-check.sh` | — | Stop soft gate: warn if `--expect` artifact missing; bounded re-block via gate-counter (independent key `stop-precheck-<sid>`) |

## Deploy to a driven CC (working dir = where `claude` runs)

```bash
DST="$PWD/.claude"            # the driven CC's working dir
mkdir -p "$DST/hooks"
cp cc-posttool.sh cc-stop-check.sh "$DST/hooks/"
# merge settings.template.json's "hooks" block into $DST/settings.json
# (if settings.json exists, merge with jq; do NOT clobber existing keys)
```

## ⚠️ Smoke BEFORE relying on the hooks (plan §3.3/§3.4 prerequisites)

These were unit-tested in isolation (`tests/test-hooks.sh`, 14/14) but the live
firing depends on the target CC version. Smoke on the actual CC build:

1. **PostToolUse fires** in interactive mode (not just `claude -p`).
2. Field names: `tool_response`, `tool_input.file_path` (MultiEdit may use
   `edits[]` → archival skips, which is handled).
3. `$CLAUDE_SESSION_ID` is exported into the hook env (else artifacts land in
   `unknown/` — not lost, just unclassified).
4. **Notification** matcher names `idle_prompt|permission_prompt` actually match.
5. **Stop** `decision:block` + `reason` round-trips. Only deploy the Stop hook
   where an `--expect` glob is being written by `cc-send.sh`, or it is a no-op.

## ⛔ Known gap — D-4 expect-file key mismatch (deferred design decision)

The shared expected-artifacts mechanism is **not wired end-to-end** by default:

- `cc-send.sh --expect` writes `/tmp/cc-expect-<TMUX_SESSION_NAME>`.
- `cc-stop-check.sh` reads `/tmp/cc-expect-<CLAUDE_SESSION_ID>` (the CC's internal
  UUID, **≠** the tmux session name).

So the keys do not match and the Stop soft gate **safely no-ops** (it never finds
an expect file → never blocks → degrades, never wedges). To make it functional,
a future change must unify the key across the tmux side and the in-CC hook side
(e.g. SessionStart records the tmux name into a UUID-keyed file, or cc-send is
taught the UUID). The `CC_EXPECT_FILE` env override is the wiring point for a
manual/temporary bridge. Same root cause blocks cc-finish from cleaning
`/tmp/cc-counter-stop-precheck-<uuid>.json`.

Status: deferred by owner decision (2026-06-17) — record the design choice before
wiring. The gate is safe (no false blocks) in the meantime.

## Cleanup contract

`cc-finish.sh` step 7 must also remove the independent counter file
`/tmp/cc-counter-stop-precheck-<sid>.json` alongside the other per-session state
(`cc-heartbeat-<sid>`, `cc-state-<sid>.log`, `cc-expect-<sid>`).
