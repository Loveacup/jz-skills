# Pre-start cleanup before launching a new CC task

Session-derived pattern from an AI-MUD UI task (2026-06-26). Use when `cc-start.sh` refuses with exit 3 because other `hermes-cc-*` sessions are active, and the user asks to clean up before launching.

## Goal

Clean only what is safe, preserve active work, then start the requested task with explicit `--ack-active` if active sessions remain and the user accepts parallelism.

## Procedure

1. Run a read-only scan first:

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-gc.sh --mode scan
```

Relay the `===📡 BEGIN ... END===` block verbatim.

2. If scan reports zombies, clean **only orphan files**:

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-gc.sh --mode gc --apply
```

This must not kill live sessions. It only removes locks/state for sessions that are already dead.

3. For completed/IDLE sessions, use `cc-finish.sh` rather than raw `tmux kill-session`:

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-finish.sh \
  --session <session> \
  --target <target> \
  --release-lock \
  --kill-session \
  --clean-topic-map
```

If the session is historical and `cc-finish` refuses due to stale monitoring gap, use `--force` only after confirming it is completed/IDLE or otherwise intentionally being retired:

```bash
... cc-finish.sh ... --force
```

4. Never kill `active-skip` / TOOL / THINKING sessions just to make the scan clean. Monitor them if needed, but leave them alone unless the user explicitly authorizes killing.

5. Re-run scan:

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-gc.sh --mode scan
```

If no safe cleanup remains but active sessions still exist, explain that active work remains. If the user already chose to proceed after cleanup, start the new task with `--ack-active`.

## Safety rules

- Do not press Enter on residual non-dangerous input found by `cc-finish`. Try safe clear keys if appropriate, but if they fail, report and leave the session as evidence.
- Do not convert “TOOL but very old” into “safe to kill” automatically. Old panes can still contain state or queued work.
- Prefer releasing locks over killing sessions. Killing is only for completed/test sessions when user allowed cleanup or when the session is clearly disposable.

## Why this matters

The user may say “先清理/收尾旧 CC，再启动”. That does **not** mean kill everything. It means:

```text
clean zombies + finish completed sessions + preserve active sessions + then launch with explicit acknowledgement
```