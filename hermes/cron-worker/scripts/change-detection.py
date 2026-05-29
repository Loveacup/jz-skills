#!/usr/bin/env python3
"""Change-detection heartbeat template.

Usage in cronjob:
  cronjob(
      name="your-monitor",
      schedule="*/15 * * * *",
      script="change-detection.py",
      prompt="State changed. Analyze:\n{SCRIPT_OUTPUT}",
      profile="cron-worker",
  )

Strategy:
  - compute_current_hash() → your domain-specific state hash
  - Compare with LAST_HASH_FILE
  - If same → sys.exit(0) with NO stdout (empty = no agent run)
  - If different → print diff, update LAST_HASH_FILE → agent fires
"""

import sys
import hashlib
from pathlib import Path

LAST_HASH_FILE = Path.home() / ".hermes/cron-worker/hashes/your-monitor.txt"

# ── Replace this with your actual state computation ─────────────────────
def compute_current_hash() -> str:
    """Return a hash representing the current state you care about."""
    # Example: hash of a web page
    # import urllib.request
    # html = urllib.request.urlopen("https://example.com/status").read()
    # return hashlib.sha256(html).hexdigest()
    return ""


# ── Main ────────────────────────────────────────────────────────────────
def main():
    current = compute_current_hash()
    if not current:
        print("ERROR: compute_current_hash returned empty", file=sys.stderr)
        sys.exit(1)

    LAST_HASH_FILE.parent.mkdir(parents=True, exist_ok=True)

    if LAST_HASH_FILE.exists():
        previous = LAST_HASH_FILE.read_text().strip()
        if previous == current:
            # No change — stay silent, no agent run
            sys.exit(0)

    # Change detected — output goes to agent
    print(f"State changed. Previous hash: {previous if 'previous' in dir() else 'N/A (first run)'}")
    print(f"Current hash: {current}")

    LAST_HASH_FILE.write_text(current)
    sys.exit(0)


if __name__ == "__main__":
    main()
