#!/usr/bin/env python3
"""Hermes cron shim for mac-doctor adapters.

Hermes refuses cron scripts whose real path is outside the profile's scripts/
directory, so the cron-worker cannot symlink to the skill. COPY this file (do not
symlink) into ``<hermes>/profiles/cron-worker/scripts/`` as
``mac-doctor-watchdog.py`` and/or ``mac-doctor-triage.py``; the file name selects
the adapter. Skill location: ``MAC_DOCTOR_SKILL_DIR`` or
``<account home>/.agents/shared/mac-doctor``.
"""
import os
import pwd
import runpy
import sys
from pathlib import Path

ADAPTERS = {"mac-doctor-watchdog.py": "watchdog.py", "mac-doctor-triage.py": "triage.py"}


def main() -> None:
    name = Path(__file__).name
    adapter_name = ADAPTERS.get(name)
    if adapter_name is None:
        sys.exit(f"mac-doctor cron shim: unknown shim name {name!r}; expected one of {sorted(ADAPTERS)}")
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    skill_dir = Path(os.environ.get("MAC_DOCTOR_SKILL_DIR") or home / ".agents" / "shared" / "mac-doctor")
    adapter = skill_dir / "adapters" / "hermes" / adapter_name
    if not adapter.is_file():
        sys.exit(f"mac-doctor cron shim: adapter not found: {adapter}")
    sys.argv[0] = str(adapter)
    runpy.run_path(str(adapter), run_name="__main__")


if __name__ == "__main__":
    main()
