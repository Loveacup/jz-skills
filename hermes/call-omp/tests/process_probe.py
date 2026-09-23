#!/usr/bin/env python3
"""ps-based process probe with contract-bound classification (EXT-01).

Classification contract (hermes-external-producer-contract.v1, EXT-01):
- Only ``ps -p`` returncode 1 with empty stdout AND empty stderr may mean
  absent/dead.
- returncode 0 with exactly one supported identity row means alive, or
  zombie when the stat column starts with ``Z``.
- Any stderr, unsupported output, timeout, or other nonzero returncode is
  unknown — never dead.
"""
import subprocess
import time

PS_FORMAT = "pid=,ppid=,pgid=,sess=,stat=,comm=,lstart="


def parse_identity(stdout):
    """Parse one ``ps -o pid=,ppid=,pgid=,sess=,stat=,comm=,lstart=`` row.

    Returns the identity dict, or None when the output is not exactly one
    supported single-process row (callers must treat None as unsupported).
    """
    lines = [line for line in stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        return None
    fields = lines[0].split()
    if len(fields) < 7:
        return None
    if not all(fields[i].isdigit() for i in range(4)):
        return None
    return {
        "pid": int(fields[0]),
        "ppid": int(fields[1]),
        "pgid": int(fields[2]),
        "sid": int(fields[3]),
        "stat": fields[4],
        "command": fields[5],
        "start_time": " ".join(fields[6:]),
    }


def classify(returncode, stdout, stderr):
    """Map one ps query result to alive / zombie / dead / unknown."""
    if stderr.strip():
        return "unknown"
    if returncode == 0:
        identity = parse_identity(stdout)
        if identity is None:
            return "unknown"
        return "zombie" if identity["stat"].startswith("Z") else "alive"
    if returncode == 1 and not stdout.strip():
        return "dead"
    return "unknown"


def probe(pid, timeout=10):
    """Query one PID; query errors classify as unknown instead of raising."""
    argv = ["ps", "-p", str(pid), "-o", PS_FORMAT]
    record = {"pid": pid, "argv": argv, "observed_at": time.time_ns()}
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        record.update({
            "state": "unknown", "exit_code": None, "query_error": "timeout",
            "stdout": exc.stdout or "", "stderr": exc.stderr or "",
        })
        return record
    record.update({
        "state": classify(result.returncode, result.stdout, result.stderr),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    })
    if record["state"] in ("alive", "zombie"):
        record["identity"] = parse_identity(result.stdout)
    return record
