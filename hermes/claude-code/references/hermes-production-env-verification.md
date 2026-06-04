# Hermes production env verification after CC deployment

Use when Claude Code edits or deploys Hermes/A2A code that runs under launchd, gateway, or another long-lived service. The parent Hermes session may be running under a profile sandbox where `~`, `HOME`, and `HERMES_HOME` do **not** match the production daemon.

## Trigger signals

- CC says it synced code to `~/.hermes/plugins/...` or restarted a Hermes daemon.
- The current Hermes profile is not the production/default profile.
- Verification from the parent session contradicts CC's claim (for example, imports resolve to an old file or `default_sinks()` shows old behavior).
- A launchd service, gateway worker, or profile-scoped process is involved.

## Rule

Do not verify production behavior using the parent session's implicit `~` or environment. Reproduce the target service environment explicitly, then import/run from the same paths the service uses.

## Procedure

1. Inspect the service environment first.
   - For launchd: `launchctl print gui/$(id -u)/<label>` and read `HOME`, `HERMES_HOME`, `PYTHONPATH`, working directory, pid, and custom env flags.
   - For Hermes gateway/profile processes: inspect the actual service unit/config and logs, not the current profile defaults.
2. Check both candidate paths if a profile sandbox is active:
   - Production/global example: `/Users/alexcai/.hermes/plugins/hermes-a2a/...`
   - Profile sandbox example: `/Users/alexcai/.hermes/profiles/regent/home/.hermes/plugins/hermes-a2a/...`
3. Run verification with explicit env matching the service, e.g.:

   ```bash
   HOME=/Users/alexcai \
   HERMES_HOME=/Users/alexcai/.hermes \
   PYTHONPATH=/Users/alexcai/.hermes/plugins/hermes-a2a \
   /opt/homebrew/bin/python3.12 - <<'PY'
   import inspect
   import event_bridge.daemon as d
   from event_bridge.daemon import default_sinks
   print('daemon_file=', inspect.getfile(d))
   print('sinks=', [s.name for s in default_sinks()])
   PY
   ```

4. If production uses launchd, verify after restart:
   - `plutil -lint <plist>`
   - `launchctl bootout ... || true`
   - `launchctl bootstrap ...`
   - `launchctl print ...` → state, pid, env flags
5. Validate behavior with real artifacts/logs, not just imports:
   - expected new files/logs exist;
   - disabled sinks/tools are actually skipped in logs;
   - source-of-truth and derived store reconcile if relevant.

## Pitfall from 2026-06-01

A regent session had `HOME=/Users/alexcai/.hermes/profiles/regent/home` while production launchd ran with `HOME=/Users/alexcai` and `HERMES_HOME=/Users/alexcai/.hermes`. A naive import from the parent session resolved to the profile sandbox and falsely suggested deployment had not taken effect. Re-running with launchd's explicit env showed the production plugin copy was correct.

## Acceptance criteria

- The import path printed by `inspect.getfile()` is the intended production file.
- The service's live env contains the expected flags/paths.
- The service has a new pid after restart when restart is part of the change.
- Runtime logs/artifacts confirm the intended behavior.
- Any destructive follow-up (remote memory cleanup, deleting historical logs, etc.) remains gated behind explicit user approval and dry-run output.
