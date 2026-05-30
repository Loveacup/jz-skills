#!/usr/bin/env python3
"""Change-detection heartbeat template for Hermes cron-worker.

Wake-gate contract:
  - Script's stdout is auto-prepended to the prompt as "## Script Output".
  - Last non-empty line = `{"wakeAgent": false}` → agent run SKIPPED.
  - Any other output → agent fires with full prompt context.

Hash persistence: state hash stored in LAST_HASH_FILE. Only changes trigger agent.

Usage in cronjob:
  cronjob(
      action="create",
      name="your-monitor",
      schedule="*/15 * * * *",
      script="change-detection.py",
      prompt="State changed. Analyze and alert if needed.",
      profile="cron-worker",
      model={"model": "deepseek-v4-flash", "provider": "deepseek"},
  )
"""

import json
import sys
import hashlib
from pathlib import Path

LAST_HASH_FILE = Path.home() / ".hermes/cron-worker/hashes/your-monitor.txt"


def compute_current_hash() -> str:
    """Return a hash representing the current state you care about.

    Replace this with your actual domain logic. Examples:
      - Hash of a web page: hashlib.sha256(requests.get(url).content).hexdigest()
      - Hash of file listing: hashlib.sha256(b'\n'.join(sorted(os.listdir(dir)))).hexdigest()
      - Hash of API response: hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    """
    return hashlib.sha256(b"replace-me").hexdigest()


def main():
    current = compute_current_hash()
    if not current:
        print("ERROR: compute_current_hash returned empty", file=sys.stderr)
        sys.exit(1)

    LAST_HASH_FILE.parent.mkdir(parents=True, exist_ok=True)

    previous = None
    if LAST_HASH_FILE.exists():
        previous = LAST_HASH_FILE.read_text().strip()

    if previous == current:
        # No change — wake-gate: skip agent run
        print(json.dumps({"wakeAgent": False}))
        sys.exit(0)

    # Change detected — agent fires
    if previous:
        print(f"State changed. Previous hash: {previous}")
    else:
        print("State changed. First run — no previous hash.")
    print(f"Current hash: {current}")

    LAST_HASH_FILE.write_text(current)
    sys.exit(0)


if __name__ == "__main__":
    main()
