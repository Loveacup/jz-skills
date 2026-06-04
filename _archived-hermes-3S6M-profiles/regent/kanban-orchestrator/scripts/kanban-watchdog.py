#!/usr/bin/env python3
"""Kanban watchdog v2 — auto-discovers ALL active tasks, no track file needed.
Runs as a cron script (no_agent=True). Reports state changes via stdout.
Silent when nothing changes. Delivered to user's chat by cron delivery."""
import subprocess, json, sys
from pathlib import Path

_HERMES_HOME = Path('~/.hermes')
STATE_FILE = _HERMES_HOME / 'profiles/regent/state/kanban-watchdog-state.json'

ICONS = {'done': '✅', 'running': '🔄', 'todo': '⏳', 'blocked': '🚫', 'failed': '❌'}

def kanban_list_active():
    """Get all non-archived, non-done tasks."""
    try:
        p = subprocess.run(['hermes', 'kanban', 'list', '--json'],
                          capture_output=True, text=True, timeout=15)
        tasks = json.loads(p.stdout)
        active = [t for t in tasks if t.get('status') not in ('done',)]
        return {t['id']: {'status': t['status'],
                          'title': t.get('title', t['id'][:10]),
                          'assignee': t.get('assignee', '?')}
                for t in active}
    except Exception:
        return {}

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))

def main():
    current = kanban_list_active()
    if not current:
        return

    old = load_state()
    changes = []

    for tid, info in current.items():
        new_status = info['status']
        old_status = old.get(tid, 'unknown')
        if old_status != new_status:
            icon = ICONS.get(new_status, '❓')
            label = info['title'] if len(info['title']) < 30 else info['title'][:27] + '…'
            changes.append(f"{icon} `{info['assignee']}` {label} → {new_status}")

    # Detect disappeared tasks (archived/deleted)
    for tid in old:
        if tid not in current:
            changes.append(f"🗄️ `{tid[:10]}` 已归档/移除")

    if changes:
        lines = ["📡 Kanban 状态变更"]
        lines.extend(f"  {c}" for c in changes)
        print('\n'.join(lines))

    save_state({tid: info['status'] for tid, info in current.items()})

if __name__ == '__main__':
    main()
