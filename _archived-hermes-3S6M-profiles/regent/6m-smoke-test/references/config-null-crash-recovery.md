# Profile config null-section crash recovery

> Discovered 2026-05-29 during 6m-smoke-test v2.
> Affected: planner, reviewer, protocol, tester, archivist profiles.

## Symptom

Kanban worker repeatedly crashes (8-52s per attempt), eventually circuit-breaker blocks the card:

```
hermes kanban runs <task_id>
#    OUTCOME       PROFILE            ELAPSED  STARTED
  1  crashed       planner                51s  2026-05-29 20:35
     ✖ pid 81099 not alive
```

Manual run shows:
```
AttributeError: 'NoneType' object has no attribute 'get'
  File "cli.py", line 2943, in __init__
    _raw_tp = CLI_CONFIG["display"].get("tool_progress", "all")
```

## Root cause

`config.yaml` has `agent: null` and/or `display: null` at root level.
Hermes CLI expects these to be dicts with sub-keys, not null.

## Detection

```bash
for p in planner reviewer protocol tester archivist; do
  echo "$p: $(grep -E '^(agent|display):' ~/.hermes/profiles/$p/config.yaml)"
done
# Bad output:
# planner:
# agent: null
# display: null
```

## Fix

```bash
for p in planner reviewer protocol tester archivist; do
  sed -i '' 's/^agent: null$/agent:\n  disabled_toolsets: []/' ~/.hermes/profiles/$p/config.yaml
  sed -i '' 's/^display: null$/display:\n  tool_progress: all/' ~/.hermes/profiles/$p/config.yaml
done
```

## Post-fix A2A restart

A2A servers cache profile config at startup. After fixing config.yaml:

```bash
# Get ports from s6m-config/port-map.md or doctor.sh
for port in 8728 8761 8833 8755 8804; do
  lsof -tiTCP:$port -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null
done
# Wait 35s for launchd auto-restart
sleep 35
# Verify
for port in 8728 8761 8833 8755 8804; do
  echo -n "port $port: "
  curl -s --max-time 3 http://127.0.0.1:$port/health
done
```

## Verification

```bash
# Manual smoke test per profile
HOME=/Users/alexcai hermes -p planner chat -q "say ok" --max-turns 1

# Unblock and retry the Kanban task
hermes kanban unblock <task_id>
```
