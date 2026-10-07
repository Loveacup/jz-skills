from __future__ import annotations

import os
import plistlib
import re
import shutil
import time


from ..paths import account_home
from ..runner import check, Command, redact
from . import command_text, result


@check("devenv.brew_outdated", "devenv", "Outdated Homebrew packages")
def brew_outdated(command: Command, timeout: float):
    started = time.monotonic()
    brew = shutil.which("brew")
    if not brew:
        return result("devenv.brew_outdated", "devenv", "skip", "Outdated Homebrew packages", evidence="Homebrew not installed", source="brew executable lookup", started=started)
    # stdout only: brew writes API-refresh progress ("==> Downloading…", "✔︎ JSON API…") to stderr.
    rc, stdout, stderr = command([brew, "outdated", "--quiet"], timeout)
    if rc:
        state, count, evidence = "unknown", None, redact(stderr or stdout)[:300]
    else:
        rows = [line.strip() for line in stdout.splitlines() if line.strip()]
        count = len(rows)
        state = "warn" if count else "pass"
        evidence = f"{count} outdated package(s)" + (f": {', '.join(rows[:10])}" if rows else "")
    return result("devenv.brew_outdated", "devenv", state, "Outdated Homebrew packages", value=count, unit="count", evidence=evidence, source="brew outdated", started=started)


@check("devenv.brew_doctor", "devenv", "Homebrew diagnostics")
def brew_doctor(command: Command, timeout: float):
    started = time.monotonic()
    brew = shutil.which("brew")
    if not brew:
        return result("devenv.brew_doctor", "devenv", "skip", "Homebrew diagnostics", evidence="Homebrew not installed", source="brew executable lookup", started=started)
    rc, stdout, stderr = command([brew, "doctor"], timeout)
    text = "\n".join(part for part in (stdout, stderr) if part)
    warning_lines = [line for line in text.splitlines() if re.match(r"\s*Warning:", line, re.I)]
    non_tier_warnings = [line for line in warning_lines if "Tier 2 configuration" not in line]
    if non_tier_warnings:
        state = "warn"
    elif "Tier 2 configuration" in text:
        state = "pass"
    elif rc:
        state = "warn" if warning_lines else "unknown"
    else:
        state = "warn" if warning_lines else "pass"
    evidence = text[:600] if text else ("No diagnostics reported" if not rc else "brew doctor returned non-zero without diagnostics")
    return result("devenv.brew_doctor", "devenv", state, "Homebrew diagnostics", evidence=evidence, source="brew doctor", started=started)


@check("devenv.dead_launchagents", "devenv", "LaunchAgents with missing program paths")
def dead_launchagents(command: Command, timeout: float):
    started = time.monotonic()
    folder = account_home() / "Library" / "LaunchAgents"

    try:
        plist_paths = sorted(folder.glob("*.plist"))
        folder.stat()
    except FileNotFoundError:
        return result("devenv.dead_launchagents", "devenv", "pass", "LaunchAgents with missing program paths", value=[], unit="count", evidence="LaunchAgents directory absent", source="plist files under account home", started=started)
    except OSError as exc:
        return result("devenv.dead_launchagents", "devenv", "unknown", "LaunchAgents with missing program paths", evidence=f"cannot inspect LaunchAgents: {exc}", source="LaunchAgents plist files", started=started)
    dead = []
    unreadable = []
    for plist_path in plist_paths:
        try:
            with plist_path.open("rb") as stream:
                item = plistlib.load(stream)
            args = item.get("ProgramArguments")
            program = args[0] if isinstance(args, list) and args else item.get("Program")
            if isinstance(program, str) and program.startswith("/") and not os.path.exists(program):
                dead.append({"label": plist_path.name, "program": program})
        except (OSError, plistlib.InvalidFileException, ValueError):
            unreadable.append(plist_path.name)
    if unreadable:
        state = "unknown"
    else:
        state = "warn" if dead else "pass"
    evidence = "; ".join(f"{x['label']} → {x['program']}" for x in dead[:20])
    if unreadable:
        evidence += ("; " if evidence else "") + "unreadable: " + ", ".join(unreadable[:10])
    return result("devenv.dead_launchagents", "devenv", state, "LaunchAgents with missing program paths", value=dead, unit="count", evidence=evidence or "No missing executable paths", source="LaunchAgents plist files", started=started)
