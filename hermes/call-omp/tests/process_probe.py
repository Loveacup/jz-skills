#!/usr/bin/env python3
"""Fail-closed process observation; only literal-empty rc=1 proves absence.

Darwin ps's sess is not the POSIX numeric SID. Use getsid(), bracketed by
identity reads, and command as the last column with unlimited output width.
This is an observation, not an atomic process handle or an argv reconstruction.
"""
import datetime
import os
import re
import subprocess
import time

PS_FORMAT = "pid=,ppid=,pgid=,stat=,lstart=,command="
# Documented Darwin/Linux states and modifiers; unfamiliar states stay unknown.
STAT = re.compile(r"[IDRSTUZ][<N>AEJL lSsVWXY+]*".replace(" ", ""))
START = re.compile(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun) "
                   r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
                   r"([0-9]{1,2}) ([0-9]{2}):([0-9]{2}):([0-9]{2}) ([0-9]{4})")
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def parse_identity(stdout):
    """Parse exactly one supported C-locale row, retaining the full command."""
    if not isinstance(stdout, str):
        return None
    lines = stdout.splitlines()
    if len(lines) != 1:
        return None
    fields = lines[0].split(None, 9)
    if len(fields) != 10 or not all(re.fullmatch(r"[0-9]+", s) for s in fields[:3]):
        return None
    pid, ppid, pgid = map(int, fields[:3])
    if pid <= 0 or pgid <= 0 or not STAT.fullmatch(fields[3]):
        return None
    start = " ".join(fields[4:9])
    match = START.fullmatch(start)
    if not match:
        return None
    weekday, month, day, hour, minute, second, year = match.groups()
    try:
        dt = datetime.datetime(int(year), MONTHS.index(month) + 1, int(day),
                               int(hour), int(minute), int(second))
    except ValueError:
        return None
    if "Mon Tue Wed Thu Fri Sat Sun".split()[dt.weekday()] != weekday:
        return None
    command = fields[9].rstrip()
    if not command or any(ord(c) < 32 or ord(c) == 127 for c in command):
        return None
    return {"pid": pid, "ppid": ppid, "pgid": pgid, "stat": fields[3],
            "command": command, "start_time": start}


def classify(returncode, stdout, stderr):
    """No whitespace normalization is allowed on the absence/error predicate."""
    if stderr != "":
        return "unknown"
    if returncode == 1 and stdout == "":
        return "dead"
    if returncode == 0:
        identity = parse_identity(stdout)
        if identity is not None:
            return "zombie" if identity["stat"].startswith("Z") else "alive"
    return "unknown"


def probe(pid, timeout=10):
    """Return unknown on any query failure, including getsid/identity races."""
    argv = ["/bin/ps", "-ww", "-p", str(pid), "-o", PS_FORMAT]
    record = {"pid": pid, "argv": argv, "observed_at": time.time_ns()}
    deadline = time.monotonic() + timeout
    try:
        if isinstance(pid, bool) or not str(pid).isascii() or not str(pid).isdigit() or int(pid) <= 0:
            raise ValueError("expected one positive numeric PID")
        env = dict(os.environ, LC_ALL="C", LANG="C")
        def query():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout)
            return subprocess.run(argv, text=True, capture_output=True,
                                  timeout=remaining, env=env)
        result = query()
        record.update(state=classify(result.returncode, result.stdout, result.stderr),
                      exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
        if record["state"] in ("alive", "zombie"):
            identity = parse_identity(result.stdout)
            if identity["pid"] != int(pid):
                raise ValueError("query PID mismatch")
            sid = os.getsid(int(pid))
            if not isinstance(sid, int) or sid <= 0:
                raise ValueError("unsupported numeric SID")
            confirm = query()
            record["confirmation"] = {"exit_code": confirm.returncode,
                                      "stdout": confirm.stdout, "stderr": confirm.stderr}
            if (classify(confirm.returncode, confirm.stdout, confirm.stderr) != record["state"]
                    or parse_identity(confirm.stdout) != identity or os.getsid(int(pid)) != sid):
                raise ValueError("identity changed during SID observation")
            identity["sid"] = sid
            record["identity"] = identity
            record["sid_source"] = "POSIX getsid(pid), bracketed by matching ps identities"
    except Exception as exc:
        record.update(state="unknown", query_error=type(exc).__name__)
        record.pop("identity", None)
        record.setdefault("exit_code", None)
        record.setdefault("stdout", "")
        record.setdefault("stderr", "")
        # TimeoutExpired may carry bytes despite text=True; preserve JSON-safe evidence.
        if isinstance(exc, subprocess.TimeoutExpired):
            for key in ("stdout", "stderr"):
                value = getattr(exc, key, None)
                if value is not None:
                    record[key] = value.decode("utf-8", "backslashreplace") if isinstance(value, bytes) else value
    return record
