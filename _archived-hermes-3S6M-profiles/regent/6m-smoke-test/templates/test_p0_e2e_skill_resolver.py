# E2E test template for skill_resolver validation.
# Copy this and customize for your specific P0 validation needs.
#
# Usage: python tests/e2e/test_p0_e2e_skill_resolver.py
#
# Key patterns demonstrated:
#   1. hermes kanban create uses POSITIONAL title (not --title flag)
#   2. Always use --json for machine-parseable output
#   3. kanban show --json returns {task: {...}, latest_summary: ..., runs: [...]}
#   4. Access task fields via card['task']['status'], NOT card['status']
#   5. Poll with 10s interval, 180s timeout per card
#   6. Schedule background with notify_on_complete=true for long-running tests

import subprocess, sys, time, json

TIMEOUT_PER_CARD = 180
POLL_INTERVAL = 10

def hermes(*args, timeout=30):
    p = subprocess.run(["hermes"] + list(args), capture_output=True, text=True, timeout=timeout)
    return p.stdout.strip(), p.stderr.strip(), p.returncode

def kanban_create(title, assignee, skill, body):
    args = ["kanban", "create", title, "--assignee", assignee, "--body", body, "--json"]
    if skill:
        args.extend(["--skill", skill])
    stdout, stderr, rc = hermes(*args)
    if rc != 0:
        return None
    return json.loads(stdout).get("id")

def kanban_show(card_id):
    stdout, stderr, rc = hermes("kanban", "show", card_id, "--json")
    if rc != 0:
        return None
    return json.loads(stdout)

def card_status(card):
    return card.get("task", {}).get("status", "unknown") if card else "unknown"

def wait_for_completion(card_id, timeout=TIMEOUT_PER_CARD):
    start = time.time()
    last_status = None
    while time.time() - start < timeout:
        card = kanban_show(card_id)
        if card is None:
            time.sleep(POLL_INTERVAL)
            continue
        status = card_status(card)
        if status != last_status:
            print(f"  [{int(time.time()-start)}s] {card_id}: {status}")
            last_status = status
        if status in ("done", "blocked", "cancelled"):
            return card
        time.sleep(POLL_INTERVAL)
    return kanban_show(card_id)

# === Your test functions here ===
# See test_p0_a1_skill_resolver.py in hermes-a2a/tests/e2e/ for full examples
