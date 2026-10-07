"""Path resolution shared by every mac-doctor component.

No component may hardcode a user name or a Hermes profile path. Resolution order
for the data directory:

1. ``MAC_DOCTOR_DATA_DIR`` (preferred) or legacy ``MAC_DOCTOR_INSPECTION_DIR``
2. ``<account home>/.hermes/inspection`` when it already exists (keeps existing
   history/preferences in place; never forks data)
3. ``<account home>/Library/Application Support/mac-doctor``

"Account home" comes from the passwd database, not ``$HOME``, because Hermes
cron profiles redirect ``$HOME`` to a profile directory.
"""
from __future__ import annotations

import os
import pwd
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]


def account_home() -> Path:
    override = os.environ.get("MAC_DOCTOR_HOME")
    if override:
        return Path(override).expanduser()
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def data_dir() -> Path:
    for key in ("MAC_DOCTOR_DATA_DIR", "MAC_DOCTOR_INSPECTION_DIR"):
        override = os.environ.get(key)
        if override:
            return Path(override).expanduser()
    home = account_home()
    legacy = home / ".hermes" / "inspection"
    if legacy.is_dir():
        return legacy
    return home / "Library" / "Application Support" / "mac-doctor"


def history_db() -> Path:
    return data_dir() / "history.db"


def config_file() -> Path:
    return data_dir() / "config.json"


def preferences_file() -> Path:
    return data_dir() / "preferences.json"


def receipts_file() -> Path:
    return data_dir() / "clean-receipts.jsonl"


def plans_dir() -> Path:
    return data_dir() / "plans"


def hermes_home() -> Path | None:
    """Hermes root if installed, else None. Only adapters/hermes may depend on it."""
    override = os.environ.get("HERMES_ROOT")
    root = Path(override).expanduser() if override else account_home() / ".hermes"
    return root if root.is_dir() else None


LAUNCHAGENT_LABEL = "com.hermes.inspection-collector"


def launchagent_plist() -> Path:
    return account_home() / "Library" / "LaunchAgents" / f"{LAUNCHAGENT_LABEL}.plist"
