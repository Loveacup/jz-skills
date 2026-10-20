#!/usr/bin/env python3
"""External-producer scenario harness (hermes-external-producer-contract.v1).

Runs one real-OMP scenario (normal | failure | cancel) against the exact
candidate commit, binding the receipt to the commit and to the SHA-256 of
every call-omp runtime file plus the executed omp binary.

Producer scope only: candidate source/tests evidence. Never Hermes-chain,
installation, or deployment acceptance. No producer-authored final verdict.
"""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import time
import uuid
import dependencies
import observe

EXPECTED_COMMIT = "3c0caa8bdcb9c6b89a066ed8a7a00adab708fd60"
EXPECTED_PARENT = "aa44eecc4630e96c82f7688a44ec2e452b8fdfae"

mode = sys.argv[1]
assert mode in ("normal", "failure", "cancel")

root = Path(__file__).resolve().parent
candidate_root = root.parents[1]
scripts = candidate_root / "hermes/call-omp/scripts"
tests = candidate_root / "hermes/call-omp/tests"
sys.path.insert(0, str(tests))
import process_probe  # noqa: E402  (contract-bound EXT-01 classifier)

# Exclusive class launch marker forbids retry even after setup failure.
marker = root / (mode + '.launch-once.json')
with marker.open('x') as f:
    json.dump({'mode': mode, 'started_ns': time.time_ns(), 'harness_sha256': dependencies.sha(__file__)}, f)
workspace = root / ("real-omp-" + mode + "-" + uuid.uuid4().hex[:12])
workspace.mkdir(mode=0o700)
state_dir = workspace.with_name(workspace.name + "-state")
state_dir.mkdir(mode=0o700)
state_path = state_dir / ("omp-state-external-producer-" + mode + ".json")
real_omp = shutil.which("omp")
assert real_omp


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tool_version(argv):
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=15)
        return (result.stdout or result.stderr).strip().splitlines()[0]
    except Exception as exc:  # evidence only; never abort the scenario
        return "unavailable: " + repr(exc)


runtime_files = sorted(p for base in (scripts, scripts.parent / "templates") for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
env = dict(os.environ, OMP_TMPDIR=str(state_dir), OMP_BIN=real_omp, PYTHONDONTWRITEBYTECODE="1")
env.pop("CALL_OMP_DEPTH", None)

if mode == "failure":
    launcher = workspace / "invalid_model_omp.py"
    launcher.write_text("#!/usr/bin/env python3\nimport os, sys\n"
                        + "binary = " + repr(real_omp) + "\n"
                        + "os.execv(binary, [binary, '--model', '__call_omp_failure_probe_nonexistent__', *sys.argv[1:]])\n")
    launcher.chmod(0o700)
    env["OMP_BIN"] = str(launcher)

receipt = {
    "schema": "call-omp-external-producer-scenario.v1",
    "mode": mode,
    "scope": ("external-producer candidate source/test evidence only; "
              "not Hermes-chain, not installation, not deployment acceptance; "
              "final verdict belongs to an independent reviewer"),
    "candidate_root": str(candidate_root),
    "candidate_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=candidate_root,
                                       text=True, capture_output=True, check=True).stdout.strip(),
    "candidate_parent": subprocess.run(["git", "log", "-1", "--format=%P"], cwd=candidate_root,
                                       text=True, capture_output=True, check=True).stdout.strip(),
    "worktree_status_porcelain": subprocess.run(["git", "status", "--porcelain"], cwd=candidate_root,
                                                text=True, capture_output=True, check=True).stdout,
    "harness_path": str(Path(__file__).resolve()),
    "harness_sha256": sha(__file__),
    "process_probe_sha256": sha(tests / "process_probe.py"),
    "lib_omp_lib_sha256": sha(scripts / "lib/omp-lib.sh"),
    "resource_supervisor_sha256": sha(scripts / "omp-resource-supervisor.py"),
    "runtime_sha256": {str(p.relative_to(candidate_root)): sha(p) for p in runtime_files},
    "omp_binary": {"requested": "omp", "path": real_omp, "sha256": sha(real_omp),
                   "version": tool_version([real_omp, "--version"])},
    "system_tools": {
        "bash": tool_version(["bash", "--version"]),
        "python3": tool_version(["python3", "-V"]),
        "jq": tool_version(["jq", "--version"]),
        "ps": "/bin/ps; -ww; numeric SID from POSIX getsid",
        "platform": tool_version(["uname", "-a"]),
    },
    "workspace": str(workspace),
    "state_path": str(state_path),
    "commands": [],
    "status": "RUNNING",
}
identities = None
unrelated = None
worker_pid = None


def command(script, *args, timeout=240):
    argv = ["bash", str(scripts / script), *map(str, args)]
    started = time.time_ns()
    with (workspace / "commands.log").open("a") as log:
        log.write("\n$ " + " ".join(argv) + "\n")
        log.flush()
        result = subprocess.run(argv, env=env, stdout=log, stderr=log, timeout=timeout)
    receipt["commands"].append({"argv": argv, "exit_code": result.returncode,
                                "started_ns": started, "finished_ns": time.time_ns()})
    return result.returncode


def resource_receipt():
    state = json.loads(state_path.read_text())
    return state, json.loads(Path(state["run"]["resource_state"]).read_text())


def wait_states(pids, wanted, deadline_s):
    deadline = time.monotonic() + deadline_s
    records = {key: process_probe.probe(pid) for key, pid in pids.items()}
    while (any(record["state"] != wanted for record in records.values())
           and time.monotonic() < deadline):
        time.sleep(0.2)
        records = {key: process_probe.probe(pid) for key, pid in pids.items()}
    return records


if mode == "normal":
    target = workspace / "normalize.py"
    target.write_text("def normalize(text):\n    return text\n")
    task = ("Edit normalize.py in the specified cwd. Implement normalize(text) to collapse "
            "all whitespace runs to one ASCII space, strip leading/trailing whitespace, and "
            "Unicode-casefold the result. Use read/write tools directly; do not delegate or "
            "change other files. Return a brief completion statement.")
    criterion = ["normalize('  Alpha\\tBETA\\n') returns 'alpha beta'",
                 "normalize('Straße  A') returns 'strasse a'",
                 "normalize('  ') returns ''"]
    grant_tools = ["read", "write"]
else:
    runner = workspace / "bounded_runner.py"
    runner.write_text('''import json, os, subprocess
from pathlib import Path
child = subprocess.Popen(["/bin/sleep", "45"])
root = Path(__file__).resolve().parent
ids = {"pid": os.getpid(), "pgid": os.getpgrp(), "sid": os.getsid(0), "ppid": os.getppid(), "child_ppid": os.getpid(), "child": child.pid, "child_pgid": os.getpgid(child.pid), "child_sid": os.getsid(child.pid)}
(root / "ready.tmp").write_text(json.dumps(ids))
os.replace(root / "ready.tmp", root / "ready.json")
try:
    child.wait(timeout=50)
finally:
    if child.poll() is None:
        child.terminate()
        child.wait(timeout=3)
''')
    task = ("Run exactly one bounded command using the bash tool: python3 " + str(runner)
            + ". Let it run in the foreground; the coordinator will cancel this finite test. "
            + "Do not delegate, background it, or modify files. "
            + "This is an authorized isolated cancellation fixture.")
    criterion = ["Cancellation stops the actual OMP worker and its observed bounded tool child"]
    grant_tools = ["read", "bash"]

package = {
    "task_id": "external-producer-" + mode, "channel": "shell", "mode": "execute",
    "task": task,
    "scope": {"allowed_paths": [str(workspace)], "denied_paths": [], "cwd": str(workspace)},
    "criterion": criterion,
    "threshold": {"round_limit": 3, "reject_limit": 2},
    "risk": {"level": "low", "dangerous_modes": []},
    "auditor": {"required": True, "independence_level": "independent_readonly"},
    "output": {"format": "json", "evidence_required": True},
    "capability_grant": {"contract": "call-omp.capability-grant.v1", "tools": grant_tools,
                         "approval": "non_interactive", "cwd": str(workspace), "add_dirs": []},
}
package_path = workspace / "package.json"
package_path.write_text(json.dumps(package, indent=2) + "\n")

dependency_paths = dependencies.paths(workspace)
receipt['dependencies_before'] = dependencies.manifest(dependency_paths)
receipt['watched_before'] = observe.snapshot()
receipt['coverage_limit'] = 'Known scripts/templates/harness/fixtures/interpreters/OMP/system utilities/stdlib bound by bytes. Dynamic OMP startup extension/MCP/config/native shared-cache loads not traced: BLOCKED; no claim of exhaustive runtime load closure.'
(root / (mode + '-dependencies-before.json')).write_text(json.dumps(receipt['dependencies_before'], indent=2) + '\n')
try:
    assert receipt["candidate_commit"] == EXPECTED_COMMIT
    assert receipt["candidate_parent"] == EXPECTED_PARENT
    tracked_drift = [line for line in receipt["worktree_status_porcelain"].splitlines()
                     if line.strip() and not line.split(None, 1)[1].startswith(".local/")]
    assert tracked_drift == [], tracked_drift
    assert command("omp-start.sh", "--package-json", package_path) == 0
    assert command("omp-send.sh", "--state", state_path, "--async", "--max-time", "90") == 0

    if mode == "normal":
        assert command("omp-monitor.sh", "--state", state_path, "--watch",
                       "--interval", "1", "--timeout", "180") == 0
        state, resource = resource_receipt()
        receipt["resource_receipt"] = resource
        assert resource["worker_exit_code"] == 0
        assert resource["cleanup_confirmed"] is True
        receipt['consumer_executed_artifact_before_sha256'] = sha(target)
        normalize = runpy.run_path(str(target))["normalize"]
        receipt['consumer_executed_artifact_after_sha256'] = sha(target)
        cases = [("  Alpha\tBETA\n", "alpha beta"), ("Straße  A", "strasse a"), ("  ", "")]
        receipt["consumer_cases"] = [{"input": value, "expected": expected,
                                      "actual": normalize(value)} for value, expected in cases]
        assert all(item["actual"] == item["expected"] for item in receipt["consumer_cases"])
        receipt["artifact_sha256"] = sha(target)
        receipt["attempt_id"] = state["run"]["attempt_id"]
        receipt["launch_fingerprint"] = state["run"]["launch_fingerprint"]
        receipt["accept_exit_code"] = command("omp-finish.sh", "--state", state_path, "--accept")
        assert receipt["accept_exit_code"] == 0
        assert json.loads(state_path.read_text())["status"] == "accepted"

    elif mode == "failure":
        assert command("omp-monitor.sh", "--state", state_path, "--watch",
                       "--interval", "1", "--timeout", "180") != 0
        state, resource = resource_receipt()
        receipt["resource_receipt"] = resource
        receipt["attempt_id"] = state["run"]["attempt_id"]
        receipt["launch_fingerprint"] = state["run"]["launch_fingerprint"]
        assert state["status"] == "rejected"
        assert resource["worker_exit_code"] not in (None, 0)
        assert resource["cleanup_confirmed"] is True
        receipt["accept_exit_code"] = command("omp-finish.sh", "--state", state_path, "--accept")
        assert receipt["accept_exit_code"] != 0

    else:  # cancel
        ready = workspace / "ready.json"
        deadline = time.monotonic() + 90
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert ready.exists(), "real OMP never launched the bounded tool fixture"
        identities = json.loads(ready.read_text())
        receipt["owned_identities_selfreported"] = identities
        owned = {"tool_runner": identities["pid"], "tool_child": identities["child"]}
        state = json.loads(state_path.read_text())
        run = state["run"]
        receipt["attempt_id"] = run["attempt_id"]
        receipt["launch_fingerprint"] = run["launch_fingerprint"]
        resource_before = json.loads(Path(run["resource_state"]).read_text())
        worker_pid = resource_before.get("pid")
        receipt["worker_pid_source"] = "resource_state.pid"
        if not worker_pid:
            pid_store = resource_before.get("pid_store")
            if pid_store and Path(pid_store).exists():
                worker_pid = json.loads(Path(pid_store).read_text()).get("pid")
                receipt["worker_pid_source"] = "pid_store.pid"
        if worker_pid:
            owned["omp_worker"] = worker_pid
        assert worker_pid, 'native worker PID missing'
        receipt['resource_before_stop'] = resource_before
        pid_store = resource_before.get('pid_store')
        receipt['pid_store_before_stop'] = json.loads(Path(pid_store).read_text()) if pid_store else None
        # Discover numeric ancestry only; capture commands solely for exact worker descendants.
        tree = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid='], text=True, capture_output=True, timeout=10)
        assert tree.returncode == 0 and tree.stderr == '', 'ancestry query failed'
        relations = {int(a):int(b) for a,b in (line.split() for line in tree.stdout.splitlines())}
        descendants = {worker_pid}
        while True:
            expanded = descendants | {pid for pid, parent in relations.items() if parent in descendants}
            if expanded == descendants: break
            descendants = expanded
        assert identities['pid'] in descendants and identities['child'] in descendants
        receipt['owned_ancestry'] = {str(pid):relations[pid] for pid in sorted(descendants)}
        for pid in sorted(descendants):
            if pid not in owned.values(): owned['descendant_' + str(pid)] = pid
        receipt["owned_before_stop"] = {key: process_probe.probe(pid) for key, pid in owned.items()}
        assert all(item["state"] == "alive" for item in receipt["owned_before_stop"].values())
        for key, prefix in [('tool_runner', ''), ('tool_child', 'child_')]:
            observed = receipt['owned_before_stop'][key]['identity']
            for field in ('pgid', 'sid', 'ppid'):
                assert observed[field] == identities[prefix + field], (key, field, observed, identities)
        native = receipt['pid_store_before_stop'] or resource_before
        receipt['worker_native_identity_comparison'] = {'probe': receipt['owned_before_stop']['omp_worker']['identity'], 'native': native}
        for field, native_field in [('pid','pid'), ('pgid','pgid'), ('sid','session_id')]:
            if native_field in native:
                assert receipt['owned_before_stop']['omp_worker']['identity'][field] == native[native_field]
        runner_cmd = receipt['owned_before_stop']['tool_runner']['identity']['command']
        assert str(runner) in runner_cmd and 'python' in runner_cmd
        assert '/bin/sleep 45' in receipt['owned_before_stop']['tool_child']['identity']['command']
        unrelated = subprocess.Popen(['/bin/sleep', '120'], start_new_session=True)
        receipt['unrelated_sentinel_name'] = 'repair-cancel-unrelated-sentinel'
        receipt['unrelated_sentinel_argv'] = ['/bin/sleep', '120']
        receipt["unrelated_before_stop"] = process_probe.probe(unrelated.pid)
        assert receipt["unrelated_before_stop"]["state"] == "alive"
        receipt["query_error_demo"] = process_probe.probe("not-a-pid")
        assert receipt["query_error_demo"]["state"] == "unknown"
        receipt["stop_exit_code"] = command(
            "omp-stop.sh", "--state", state_path,
            "--attempt-id", run["attempt_id"], "--launch-fingerprint", run["launch_fingerprint"],
            "--reason", "external producer owned-child cancellation scenario",
            "--timeout", "10", timeout=30)
        assert receipt["stop_exit_code"] == 0
        receipt["owned_after_stop"] = wait_states(owned, "dead", 30)
        receipt["unrelated_after_stop"] = process_probe.probe(unrelated.pid)
        assert all(item["state"] == "dead" for item in receipt["owned_after_stop"].values())
        assert receipt["unrelated_after_stop"]["state"] == "alive"
        assert receipt['unrelated_after_stop']['identity'] == receipt['unrelated_before_stop']['identity']
        state, resource = resource_receipt()
        receipt["resource_receipt"] = resource
        assert state["status"] == "rejected"
        assert resource["cleanup_confirmed"] is True
        assert resource["status"] == "rejected"
        assert resource["terminal_reason"].startswith("cancelled:")
        receipt["accept_exit_code"] = command("omp-finish.sh", "--state", state_path, "--accept")
        assert receipt["accept_exit_code"] != 0

    receipt["status"] = "SCENARIO_ASSERTIONS_SATISFIED_PRODUCER_SCOPE"
except BaseException as exc:
    receipt["status"] = "SCENARIO_FAILED"
    receipt["error"] = repr(exc)
    raise
finally:
    if unrelated is not None and unrelated.poll() is None:
        unrelated.terminate()
        try:
            unrelated.wait(timeout=5)
        except subprocess.TimeoutExpired:
            unrelated.kill()
    if state_path.exists():
        state = json.loads(state_path.read_text())
        run = state.get("run", {})
        if run.get("attempt_id") and not run.get("cleanup_confirmed"):
            receipt["finalization_stop_exit"] = command(
                "omp-stop.sh", "--state", state_path,
                "--attempt-id", run["attempt_id"], "--launch-fingerprint", run["launch_fingerprint"],
                "--reason", "scenario finalization", "--timeout", "10", timeout=30)
    if identities:
        final = dict(owned)
        if worker_pid:
            final["omp_worker"] = worker_pid
        receipt["owned_final"] = wait_states(final, "dead", 55)
    receipt['dependencies_after'] = dependencies.manifest(dependency_paths)
    # Normal task output is expected to change, its executed bytes are separately bound.
    receipt['dependency_changes'] = [p for p in receipt['dependencies_before'] if receipt['dependencies_before'][p] != receipt['dependencies_after'][p]]
    receipt['dependency_unexpected_changes'] = [p for p in receipt['dependency_changes'] if not (mode == 'normal' and p == str(target))]
    if receipt['dependency_unexpected_changes']:
        receipt['status'] = 'BLOCKED_DEPENDENCY_DRIFT'
    receipt['watched_after'] = observe.snapshot()
    receipt['final_state'] = json.loads(state_path.read_text()) if state_path.exists() else None
    receipt['native_evidence_sha256'] = {str(p):sha(p) for p in state_dir.rglob('*') if p.is_file()}
    receipt_path = workspace / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    receipt_path.chmod(0o444)
    print(json.dumps({"mode": mode, "status": receipt["status"], "receipt": str(receipt_path)},
                     ensure_ascii=False))
