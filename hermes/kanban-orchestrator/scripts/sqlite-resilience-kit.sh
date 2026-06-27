#!/usr/bin/env bash
# SQLite Resilience Kit — combined dead-worker reaper + parent-done watchdog
# Run as: no_agent=True cronjob every 5m
# Zero LLM tokens — pure shell polling
set -euo pipefail

NOW=$(date +%s)

echo "=== Dead-worker reaper ==="
hermes kanban list --json 2>/dev/null | python3 -c "
import json, sys, os
tasks = json.load(sys.stdin)
for t in tasks:
    if t.get('status') != 'running':
        continue
    runs = t.get('runs', [])
    if not runs:
        continue
    pid = runs[-1].get('pid')
    if pid is None:
        continue
    try:
        os.kill(pid, 0)
    except OSError:
        print(f'{t[\"task_id\"]} {pid}')
" | while read -r task_id pid; do
    echo "  Orphan: $task_id (pid $pid not found)"
    hermes kanban block "$task_id" "worker-exited-without-completing (pid $pid not found)" 2>/dev/null || true
    hermes kanban comment "$task_id" "[auto] Dead-worker reaper: pid $pid exited without complete/block." 2>/dev/null || true
done

echo "=== Parent-done watchdog ==="
hermes kanban list --json 2>/dev/null | python3 -c "
import json, sys
tasks = json.load(sys.stdin)
now = $NOW
for t in tasks:
    if t.get('status') != 'todo':
        continue
    parents = t.get('parents', [])
    if not parents:
        continue
    meta = t.get('metadata', {}) or {}
    timeout_at = meta.get('parent_timeout_at', 0)
    if timeout_at and now > timeout_at:
        print(f'{t[\"task_id\"]} {timeout_at} {\" \".join(parents)}')
" | while read -r task_id timeout_at parents_str; do
    STUCK=false
    for p in $parents_str; do
        PSTATUS=$(hermes kanban show "$p" 2>/dev/null | grep "^  status:" | awk '{print $2}' || echo "unknown")
        if [ "$PSTATUS" = "running" ] || [ "$PSTATUS" = "blocked" ]; then
            STUCK=true
            break
        fi
    done
    if $STUCK; then
        echo "  Stuck child: $task_id (parent timeout)"
        hermes kanban comment "$task_id" "[watchdog] Parent timeout. Parents still not done. Escalating." 2>/dev/null || true
    fi
done

echo "=== Resilience kit complete ==="
