#!/usr/bin/env python3
"""Observable execute lifecycle regressions; no real model or shared runtime."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
FIXTURE = r'''#!/usr/bin/env python3
import json, os, signal, subprocess, sys, time
from pathlib import Path
root = Path(os.environ["FIXTURE_ROOT"])
mode = os.environ.get("FIXTURE_MODE", "success")
with (root / "launches").open("a") as f:
    f.write(str(os.getpid()) + "\n")
child = None
if mode in ("slow", "leader_exit", "ignore_term"):
    child = subprocess.Popen(["/bin/sleep", "20"])
if mode == "ignore_term":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
(root / "identity.tmp").write_text(json.dumps({"pid":os.getpid(), "child":child.pid if child else None}))
os.replace(root / "identity.tmp", root / "identity.json")
print(json.dumps({"type":"session", "id":"fixture"}), flush=True)
if mode in ("slow", "ignore_term"):
    time.sleep(20)
if mode == "stderr":
    sys.stderr.write("e" * (2 * 1024 * 1024))
    sys.stderr.flush()
if mode == "stdout_flood":
    os.write(1, b"x" * 8192)
    time.sleep(20)
if mode == "business_file":
    with (root / "business.bin").open("wb") as f:
        f.write(b"x" * (21 * 1024 * 1024))
text = json.dumps({"severity":"pass", "summary":"fixture audit complete", "evidence":[{"type":"file","ref":"fixture.py:1"}]}) if mode == "audit" else "fixture complete"
print(json.dumps({"type":"message_end", "message":{"role":"assistant", "content":[{"type":"text", "text":text}]}}), flush=True)
print(json.dumps({"type":"turn_end", "message":{"stopReason":"stop"}}), flush=True)
if mode == "failure":
    sys.exit(42)
'''


def live(pid):
    if not pid:
        return False
    result = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], text=True, capture_output=True)
    return result.returncode == 0 and bool(result.stdout.strip()) and not result.stdout.strip().startswith("Z")


class ExecuteLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="call-omp-execute-")
        self.root = Path(self.tmp.name)
        self.env = dict(os.environ, OMP_TMPDIR=str(self.root), FIXTURE_ROOT=str(self.root))
        self.env.pop("CALL_OMP_DEPTH", None)
        self.fixture = self.root / "fixture.py"
        self.fixture.write_text(FIXTURE)
        self.fixture.chmod(0o700)
        self.env["OMP_BIN"] = str(self.fixture)
        self.state = self.root / "omp-state-lifecycle.json"
        self.log = (self.root / "commands.log").open("w+")

    def tearDown(self):
        try:
            if self.state.exists():
                try:
                    state = self.read_state()
                except (OSError, json.JSONDecodeError):
                    state = {}
                run = state.get("run", {})
                if run.get("attempt_id") and not run.get("cleanup_confirmed") and (SCRIPTS / "omp-stop.sh").exists():
                    self.stop(timeout=8)
            identity = self.root / "identity.json"
            if identity.exists():
                ids = json.loads(identity.read_text())
                deadline = time.monotonic() + 22
                while any(live(p) for p in ids.values()) and time.monotonic() < deadline:
                    time.sleep(.1)
                if any(live(p) for p in ids.values()):
                    self.fail("bounded fixture survived cleanup")
        finally:
            self.log.close()
            evidence = os.environ.get("CALL_OMP_TEST_EVIDENCE")
            if evidence:
                destination = Path(evidence) / self._testMethodName
                destination.mkdir(parents=True, exist_ok=True)
                for path in self.root.iterdir():
                    if path.is_file() and path.suffix in (".json", ".log"):
                        shutil.copy2(path, destination / path.name)
            self.tmp.cleanup()

    def command(self, script, *args, env=None, timeout=15):
        return subprocess.run(["bash", str(SCRIPTS / script), *map(str, args)], env=env or self.env,
                              stdout=self.log, stderr=self.log, timeout=timeout).returncode

    def read_state(self):
        return json.loads(self.state.read_text())

    def start(self, mode="success", task_mode="execute", expect=0):
        self.env["FIXTURE_MODE"] = mode
        pkg = {"task_id":"lifecycle", "channel":"shell", "mode":task_mode,
               "task":"Run isolated lifecycle fixture", "scope":{"allowed_paths":[str(self.root)], "denied_paths":[], "cwd":str(self.root)},
               "criterion":["Owned worker is stopped before terminal acceptance"],
               "threshold":{"round_limit":3,"reject_limit":2}, "risk":{"level":"low","dangerous_modes":[]},
               "auditor":{"required":True,"independence_level":"independent_readonly"},
               "output":{"format":"json","evidence_required":True},
               "capability_grant":{"contract":"call-omp.capability-grant.v1","tools":["read","bash"],
                                   "approval":"non_interactive","cwd":str(self.root),"add_dirs":[]}}
        if task_mode != "execute":
            del pkg["capability_grant"]
        path = self.root / "package.json"
        path.write_text(json.dumps(pkg))
        self.assertEqual(self.command("omp-start.sh", "--package-json", path), expect)

    def send(self):
        return self.command("omp-send.sh", "--state", self.state, "--async", "--max-time", "30")

    def identity(self):
        path = self.root / "identity.json"
        deadline = time.monotonic() + 8
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(.05)
        self.assertTrue(path.exists(), "worker never started")
        return json.loads(path.read_text())

    def stop(self, attempt=None, fingerprint=None, timeout=8):
        run = self.read_state()["run"]
        return self.command("omp-stop.sh", "--state", self.state,
                            "--attempt-id", attempt or run["attempt_id"],
                            "--launch-fingerprint", fingerprint or run["launch_fingerprint"],
                            "--reason", "regression cancellation", "--timeout", str(timeout), timeout=timeout+5)

    def receipt(self):
        run = self.read_state()["run"]
        return json.loads(Path(run["resource_state"]).read_text())

    def finish(self, decision, attempt=None, fingerprint=None, identity=True):
        args = ["--state", self.state, f"--{decision}"]
        if identity:
            run = self.read_state()["run"]
            args += ["--attempt-id", attempt or run["attempt_id"],
                     "--launch-fingerprint", fingerprint or run["launch_fingerprint"]]
        return self.command("omp-finish.sh", *args, timeout=30)

    def watch(self, timeout=8):
        return self.command("omp-monitor.sh", "--state", self.state, "--watch", "--interval", "1",
                            "--timeout", str(timeout), timeout=timeout+12)

    def test_cancel_stops_worker_and_child_without_touching_unrelated_process(self):
        self.start("ignore_term")
        self.assertEqual(self.send(), 0)
        ids = self.identity()
        unrelated = subprocess.Popen(["/bin/sleep", "20"])
        try:
            self.assertEqual(self.stop(), 0)
            self.assertFalse(any(live(p) for p in ids.values()), "cancel returned before owned group stopped")
            self.assertIsNone(unrelated.poll(), "unrelated process was signalled")
            self.assertTrue(self.receipt()["cleanup_confirmed"])
            self.assertEqual(self.receipt()["worker_exit_code"], -9)
            self.assertNotEqual(self.finish("accept"), 0)
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=5)

    def test_watch_timeout_stops_actual_worker_not_only_wrapper(self):
        self.start("slow")
        self.assertEqual(self.send(), 0)
        ids = self.identity()
        self.assertNotEqual(self.watch(timeout=1), 0)
        self.assertFalse(any(live(p) for p in ids.values()))
        self.assertTrue(self.receipt()["cleanup_confirmed"])

    def test_wrong_attempt_cannot_cancel_current_worker(self):
        self.start("slow")
        self.assertEqual(self.send(), 0)
        ids = self.identity()
        current = self.read_state()["run"]["attempt_id"]
        other = ("a" if current[0] != "a" else "b") + current[1:]
        self.assertNotEqual(self.stop(attempt=other), 0)
        self.assertTrue(live(ids["pid"]))
        self.assertEqual(self.stop(), 0)

    def test_nonzero_after_valid_turn_end_is_not_accepted(self):
        self.start("failure")
        self.assertEqual(self.send(), 0)
        self.assertNotEqual(self.watch(), 0)
        self.assertEqual(self.receipt()["worker_exit_code"], 42)
        self.assertEqual(self.read_state()["run"]["exit_code"], 42)
        self.assertNotEqual(self.finish("accept"), 0)

    def test_leader_exit_does_not_leave_descendant(self):
        self.start("leader_exit")
        self.assertEqual(self.send(), 0)
        ids = self.identity()
        self.watch()
        self.assertFalse(any(live(p) for p in ids.values()))
        self.assertTrue(self.receipt()["cleanup_confirmed"])

    def test_stderr_flood_does_not_deadlock_success(self):
        self.start("stderr")
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        self.assertEqual(self.receipt()["worker_exit_code"], 0)

    def supervisor_argv(self, raw_cap=20971520, control_file=None):
        return ["python3", str(SCRIPTS / "omp-resource-supervisor.py"),
                "--capture-mode", "execute_v1",
                "--state-file", str(self.root / "bounded-resource.json"),
                "--raw-output", str(self.root / "bounded.json"), "--raw-cap", str(raw_cap),
                "--pid-store", str(self.root / "bounded-identity.json"),
                "--task-id", "bounded", "--attempt-id", "d9a68d9f-9d28-4330-9ab0-8c6c8f12aa9f",
                "--launch-fingerprint", "a" * 64, "--control-file", str(control_file or self.root / "cancel.json"),
                "--max-seconds", "30", "--", str(self.fixture)]

    def test_stdout_cap_rejects_and_stops_worker_at_configured_bound(self):
        self.env["FIXTURE_MODE"] = "stdout_flood"
        raw = self.root / "bounded.json"
        resource = self.root / "bounded-resource.json"
        argv = self.supervisor_argv(raw_cap=4096)
        result = subprocess.run(argv, env=self.env, stdout=self.log, stderr=self.log, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads(resource.read_text())
        self.assertEqual(receipt["terminal_reason"], "stdout_cap_exceeded")
        self.assertTrue(receipt["cleanup_confirmed"])
        self.assertEqual(raw.stat().st_size, 4096)
        self.assertFalse(any(live(pid) for pid in self.identity().values()))

    def test_supervisor_hangup_cleans_owned_worker_and_child(self):
        self.env["FIXTURE_MODE"] = "slow"
        supervisor = subprocess.Popen(self.supervisor_argv(), env=self.env, stdout=self.log, stderr=self.log)
        try:
            ids = self.identity()
            supervisor.send_signal(signal.SIGHUP)
            self.assertNotEqual(supervisor.wait(timeout=10), 0)
            receipt = json.loads((self.root / "bounded-resource.json").read_text())
            self.assertTrue(receipt["cleanup_confirmed"])
            self.assertNotEqual(receipt["status"], "reported")
            self.assertFalse(any(live(pid) for pid in ids.values()))
        finally:
            if supervisor.poll() is None:
                supervisor.terminate()
                supervisor.wait(timeout=10)

    @unittest.skipIf(os.geteuid() == 0, "root bypasses file read permissions")
    def test_inaccessible_control_directory_still_cleans_worker(self):
        self.env["FIXTURE_MODE"] = "slow"
        control_dir = self.root / "control-dir"
        control_dir.mkdir(mode=0o700)
        supervisor = subprocess.Popen(self.supervisor_argv(control_file=control_dir / "cancel.json"),
                                      env=self.env, stdout=self.log, stderr=self.log)
        try:
            ids = self.identity()
            control_dir.chmod(0)
            self.assertNotEqual(supervisor.wait(timeout=10), 0)
            receipt = json.loads((self.root / "bounded-resource.json").read_text())
            self.assertTrue(receipt["cleanup_confirmed"])
            self.assertEqual(receipt["status"], "rejected")
            self.assertFalse(any(live(pid) for pid in ids.values()))
        finally:
            control_dir.chmod(0o700)
            if supervisor.poll() is None:
                supervisor.terminate()
                supervisor.wait(timeout=10)

    def test_output_capture_limit_does_not_limit_business_files(self):
        self.start("business_file")
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        self.assertEqual((self.root / "business.bin").stat().st_size, 21 * 1024 * 1024)

    def test_concurrent_send_launches_only_one_worker(self):
        self.start("slow")
        argv = ["bash", str(SCRIPTS / "omp-send.sh"), "--state", str(self.state), "--async", "--max-time", "30"]
        jobs = [subprocess.Popen(argv, env=self.env, stdout=self.log, stderr=self.log) for _ in range(2)]
        codes = [job.wait(timeout=15) for job in jobs]
        self.assertEqual(codes.count(0), 1, codes)
        self.identity()
        self.assertEqual(len((self.root / "launches").read_text().splitlines()), 1)
        self.assertEqual(self.stop(), 0)

    def test_trailing_tmpdir_separator_preserves_execute_lifecycle(self):
        self.env["OMP_TMPDIR"] = str(self.root) + "/"
        self.start()
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        self.assertEqual(self.finish("accept"), 0)
        self.assertEqual(self.read_state()["status"], "accepted")

    def test_native_bash_legacy_watch_accepts_zero_optional_identity_arguments(self):
        self.start("audit", task_mode="audit")
        self.assertEqual(self.send(), 0)
        result = subprocess.run(
            ["/bin/bash", str(SCRIPTS / "omp-monitor.sh"), "--state", str(self.state),
             "--watch", "--interval", "1", "--timeout", "5"],
            env=self.env, stdout=self.log, stderr=self.log, timeout=15)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.read_state()["status"], "reported")

    def test_accepted_task_remains_accepted_when_monitored_or_stopped_again(self):
        self.start()
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        self.assertEqual(self.finish("accept"), 0)
        self.assertEqual(self.command("omp-monitor.sh", "--state", self.state, "--json"), 0)
        self.assertEqual(self.read_state()["status"], "accepted")
        self.assertEqual(self.stop(), 0)
        self.assertEqual(self.read_state()["status"], "accepted")

    def test_clean_attempt_reuse_does_not_reset_task_round_limit(self):
        for _ in range(3):
            self.start("failure")
            self.assertEqual(self.send(), 0)
            self.assertNotEqual(self.watch(), 0)
        self.start("failure")
        self.assertEqual(self.send(), 20)
        self.assertEqual(len((self.root / "launches").read_text().splitlines()), 3)

    def test_old_watcher_cannot_cancel_successor_attempt(self):
        self.start("slow")
        self.assertEqual(self.send(), 0)
        previous = self.identity()
        barrier = self.root / "watch-barrier"
        release = self.root / "watch-release"
        shim_dir = self.root / "watch-bin"
        shim_dir.mkdir()
        shim = shim_dir / "sleep"
        shim.write_text(
            "#!/usr/bin/env python3\nimport os, sys, time\nfrom pathlib import Path\n"
            "ready = Path(os.environ['WATCH_BARRIER'])\n"
            "if sys.argv[1:] == ['2'] and not ready.exists():\n"
            "    ready.touch()\n    deadline = time.monotonic() + 12\n"
            "    while not Path(os.environ['WATCH_RELEASE']).exists() and time.monotonic() < deadline:\n"
            "        time.sleep(.01)\n"
            "    sys.exit(0)\n"
            "os.execv('/bin/sleep', ['sleep', *sys.argv[1:]])\n")
        shim.chmod(0o700)
        watch_env = dict(self.env, PATH=str(shim_dir) + os.pathsep + self.env["PATH"],
                         WATCH_BARRIER=str(barrier), WATCH_RELEASE=str(release))
        with (self.root / "old-watch.log").open("w") as log:
            watcher = subprocess.Popen(
                ["bash", str(SCRIPTS / "omp-monitor.sh"), "--state", str(self.state),
                 "--watch", "--interval", "2", "--timeout", "8"],
                env=watch_env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 5
                while not barrier.exists() and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(barrier.exists(), "watch never reached its first polling interval")
                old_attempt = self.read_state()["run"]["attempt_id"]
                self.assertEqual(self.stop(), 0)
                self.assertFalse(any(live(pid) for pid in previous.values()))
                (self.root / "identity.json").unlink()
                self.start("slow")
                self.assertEqual(self.send(), 0)
                successor = self.identity()
                self.assertNotEqual(old_attempt, self.read_state()["run"]["attempt_id"])
                release.touch()
                self.assertNotEqual(watcher.wait(timeout=15), 0)
                self.assertTrue(live(successor["pid"]))
                self.assertEqual(self.read_state()["status"], "running")
                self.assertEqual(self.stop(), 0)
            finally:
                release.touch()
                if watcher.poll() is None:
                    watcher.terminate()
                    watcher.wait(timeout=5)

    def test_execute_finish_requires_current_attempt_identity(self):
        self.start()
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        self.assertEqual(self.finish("accept", identity=False), 3)
        self.assertEqual(self.read_state()["status"], "reported")
        self.assertEqual(self.finish("accept"), 0)
        self.assertEqual(self.read_state()["status"], "accepted")

    def test_late_accept_from_replaced_attempt_cannot_accept_successor(self):
        self.start()
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        old = self.read_state()["run"]
        self.assertEqual(self.finish("reject"), 0)
        (self.root / "identity.json").unlink()
        self.start()
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        successor = self.read_state()["run"]
        self.assertNotEqual(old["attempt_id"], successor["attempt_id"])
        self.assertNotEqual(self.finish("accept", old["attempt_id"], old["launch_fingerprint"]), 0)
        self.assertEqual(self.read_state()["status"], "reported")
        self.assertEqual(self.read_state()["run"]["attempt_id"], successor["attempt_id"])
        self.assertEqual(self.finish("accept"), 0)

    def test_undecided_reported_attempt_is_not_replayed(self):
        # Effect committed, decision (ack) lost: a retry must reconcile, not re-execute.
        self.start()
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        first = self.read_state()["run"]
        self.start(expect=3)
        self.assertEqual(len((self.root / "launches").read_text().splitlines()), 1)
        self.assertEqual(self.read_state()["status"], "reported")
        self.assertEqual(self.read_state()["run"]["attempt_id"], first["attempt_id"])
        self.assertEqual(self.finish("accept"), 0)

    def test_accepted_attempt_is_never_replayed(self):
        self.start()
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        self.assertEqual(self.finish("accept"), 0)
        self.start(expect=3)
        self.assertEqual(len((self.root / "launches").read_text().splitlines()), 1)
        self.assertEqual(self.read_state()["status"], "accepted")

    def test_unmonitored_finished_attempt_is_not_replayed(self):
        # Effect committed and the receipt is terminal, but MONITOR never ran (its
        # acknowledgement was lost): the main state is still running. A retry must not
        # delete the receipt and execute again.
        self.start()
        self.assertEqual(self.send(), 0)
        receipt = Path(self.read_state()["run"]["resource_state"])
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if receipt.exists() and json.loads(receipt.read_text()).get("status") == "reported":
                break
            time.sleep(.1)
        self.assertEqual(json.loads(receipt.read_text())["status"], "reported")
        self.assertEqual(self.read_state()["status"], "running")
        self.start(expect=3)
        self.assertTrue(receipt.exists(), "retry deleted the unreconciled receipt")
        self.assertEqual(len((self.root / "launches").read_text().splitlines()), 1)
        self.assertEqual(self.watch(), 0)
        self.assertEqual(self.finish("accept"), 0)

    def test_late_decision_cannot_touch_gated_successor(self):
        self.start()
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        old = self.read_state()["run"]
        self.assertEqual(self.finish("reject"), 0)
        self.start()
        self.assertEqual(self.read_state()["status"], "gated")
        for decision in ("human-review", "reject", "accept"):
            self.assertEqual(self.finish(decision, old["attempt_id"], old["launch_fingerprint"]), 2)
            self.assertEqual(self.read_state()["status"], "gated")
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        self.assertEqual(self.finish("accept"), 0)

    def test_late_reject_from_replaced_attempt_cannot_stop_successor(self):
        self.start("slow")
        self.assertEqual(self.send(), 0)
        previous = self.identity()
        old = self.read_state()["run"]
        self.assertEqual(self.stop(), 0)
        self.assertFalse(any(live(pid) for pid in previous.values()))
        (self.root / "identity.json").unlink()
        self.start("slow")
        self.assertEqual(self.send(), 0)
        successor = self.identity()
        self.assertNotEqual(self.finish("reject", old["attempt_id"], old["launch_fingerprint"]), 0)
        self.assertTrue(live(successor["pid"]), "late reject stopped the successor attempt")
        self.assertEqual(self.read_state()["status"], "running")
        self.assertEqual(self.stop(), 0)

    def test_recursion_refused_before_state_or_counter_changes(self):
        self.start()
        before = {p.name:p.read_bytes() for p in self.root.glob("omp-*.json")}
        env = dict(self.env, CALL_OMP_DEPTH="1")
        self.assertNotEqual(self.command("omp-send.sh", "--state", self.state, env=env), 0)
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.root.glob("omp-*.json")})
        self.assertFalse((self.root / "launches").exists())

    def test_execute_skips_path_python_without_waitid(self):
        # A host venv python3 earlier on PATH lacks os.waitid (CPython 3.11 on macOS inside a
        # Hermes worker). Execute must still launch under a capable python3 later on PATH.
        shim = self.root / "nowaitid"
        shim.mkdir()
        (shim / "sitecustomize.py").write_text("import os\ntry:\n    del os.waitid\nexcept AttributeError:\n    pass\n")
        bad = self.root / "badbin"
        bad.mkdir()
        wrapper = bad / "python3"
        wrapper.write_text(f'#!/bin/bash\nPYTHONPATH="{shim}${{PYTHONPATH:+:$PYTHONPATH}}" exec "{shutil.which("python3")}" "$@"\n')
        wrapper.chmod(0o755)
        self.env.pop("OMP_PY", None)
        self.env["PATH"] = f"{bad}:{self.env['PATH']}"
        self.start()
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.watch(), 0)
        self.assertEqual(self.receipt()["worker_exit_code"], 0)
        self.assertNotEqual(self.read_state()["run"]["supervisor_python"], str(wrapper))

    def test_granted_execute_without_acceptance_criteria_never_launches(self):
        # A coordinator that grants capabilities must also state acceptance; an execute
        # package with a grant and an empty criterion list is rejected before any launch.
        pkg = {"task_id":"lifecycle", "channel":"shell", "mode":"execute",
               "task":"Run isolated lifecycle fixture", "scope":{"allowed_paths":[str(self.root)], "denied_paths":[], "cwd":str(self.root)},
               "criterion":[], "threshold":{"round_limit":3,"reject_limit":2}, "risk":{"level":"low","dangerous_modes":[]},
               "auditor":{"required":True,"independence_level":"independent_readonly"},
               "output":{"format":"json","evidence_required":True},
               "capability_grant":{"contract":"call-omp.capability-grant.v1","tools":["read","bash"],
                                   "approval":"non_interactive","cwd":str(self.root),"add_dirs":[]}}
        path = self.root / "package.json"
        path.write_text(json.dumps(pkg))
        self.assertNotEqual(self.command("omp-start.sh", "--package-json", path), 0)
        self.send()
        self.assertFalse((self.root / "launches").exists())

    def test_prespawn_capability_refusal_reports_confirmed_cleanup(self):
        # Supervisor forced onto a python without os.waitid refuses before spawning OMP;
        # monitor must report not_started with confirmed cleanup, not cleanup_unknown.
        shim = self.root / "nowaitid"
        shim.mkdir()
        (shim / "sitecustomize.py").write_text("import os\ntry:\n    del os.waitid\nexcept AttributeError:\n    pass\n")
        wrapper = self.root / "py-nowaitid"
        wrapper.write_text(f'#!/bin/bash\nPYTHONPATH="{shim}" exec "{shutil.which("python3")}" "$@"\n')
        wrapper.chmod(0o755)
        self.env["OMP_PY"] = str(wrapper)
        self.start()
        self.assertEqual(self.send(), 0)
        self.assertNotEqual(self.watch(), 0)
        run = self.read_state()["run"]
        self.assertFalse((self.root / "launches").exists())
        self.assertTrue(run["cleanup_confirmed"])
        self.assertEqual(run["terminal_reason"], "unreaped_exit_or_signal_fence_unsupported")
        self.assertEqual(run["execution"], "not_started")
        self.assertNotEqual(self.finish("accept"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
