#!/usr/bin/env bash
# Supervision watchdog — out-of-band intervention bridge
# Run as: no_agent=True cronjob, e.g. every 15s
# Polls Kanban comments for [watchdog-intervene] prefix,
# writes to /tmp/kanban-intervene-{task_id}.md
set -euo pipefail

TASK_ID="${1:-}"
INTERVAL="${2:-15}"
INTERVENE_DIR="/tmp"

if [ -z "$TASK_ID" ]; then
    echo "Usage: $0 <task_id> [interval_seconds]" >&2
    exit 1
fi

INTERVENE_FILE="${INTERVENE_DIR}/kanban-intervene-${TASK_ID}.md"

while true; do
    STATUS=$(hermes kanban show "$TASK_ID" 2>/dev/null | grep "^  status:" | awk '{print $2}' || echo "unknown")
    if [ "$STATUS" = "done" ] || [ "$STATUS" = "blocked" ] || [ "$STATUS" = "archived" ]; then
        rm -f "$INTERVENE_FILE"
        exit 0
    fi

    NEW_INSTRUCTION=$(hermes kanban log "$TASK_ID" 2>/dev/null | grep "\[watchdog-intervene\]" | tail -1 | sed 's/.*\[watchdog-intervene\] //' || true)

    if [ -n "$NEW_INSTRUCTION" ]; then
        CURRENT=$(cat "$INTERVENE_FILE" 2>/dev/null || echo "")
        if [ "$NEW_INSTRUCTION" != "$CURRENT" ]; then
            echo "$NEW_INSTRUCTION" > "$INTERVENE_FILE"
            touch "$INTERVENE_FILE"
        fi
    fi

    sleep "$INTERVAL"
done
