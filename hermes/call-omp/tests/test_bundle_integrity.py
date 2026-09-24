#!/usr/bin/env python3
"""bundle_only audits must refuse to launch OMP when copied evidence is missing, tampered or unhashed."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


class BundleIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="call-omp-bundle-")
        self.root = Path(self.tmp.name)
        repo = self.root / "repo"
        repo.mkdir()
        (repo / "a.py").write_text("def f():\n    return 1\n")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "i", "--allow-empty"], cwd=repo, check=True)
        (repo / "a.py").write_text("def f():\n    return 2\n")
        self.bundle = self.root / "bundle"
        subprocess.run(["bash", str(SCRIPTS / "omp-bundle-code-audit.sh"), "--repo", str(repo), "--out", str(self.bundle)],
                       check=True, capture_output=True)
        mock = self.root / "mock-omp.sh"
        mock.write_text(f'#!/bin/bash\necho "$$" >> {self.root}/launches\n'
                        'echo \'{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"{\\"severity\\":\\"pass\\",\\"summary\\":\\"ok\\",\\"evidence\\":[\\"a.py:2\\"]}"}]}}\'\n'
                        'echo \'{"type":"turn_end","message":{"stopReason":"stop"}}\'\n')
        mock.chmod(0o755)
        self.env = dict(os.environ, OMP_TMPDIR=str(self.root), OMP_BIN=str(mock))
        self.env.pop("CALL_OMP_DEPTH", None)
        self.repo = repo

    def tearDown(self):
        self.tmp.cleanup()

    def run_audit(self):
        pkg = {"task_id": "bi", "channel": "shell", "mode": "audit", "task": "audit a.py",
               "scope": {"allowed_paths": [str(self.repo)], "denied_paths": [], "cwd": str(self.repo)},
               "criterion": ["f returns the documented value"], "threshold": {"round_limit": 3, "reject_limit": 2},
               "risk": {"level": "low", "dangerous_modes": []},
               "auditor": {"required": True, "independence_level": "bundle_only"},
               "evidence_bundle": {"path": str(self.bundle / "manifest.json")},
               "output": {"format": "json", "evidence_required": True}}
        p = self.root / "pkg.json"
        p.write_text(json.dumps(pkg))
        run = lambda *a: subprocess.run(["bash", str(SCRIPTS / a[0]), *a[1:]], env=self.env, capture_output=True).returncode
        self.assertEqual(run("omp-start.sh", "--package-json", str(p)), 0)
        rc = run("omp-send.sh", "--state", str(self.root / "omp-state-bi.json"), "--max-time", "20")
        state = json.loads((self.root / "omp-state-bi.json").read_text())
        return rc, state, (self.root / "launches").exists()

    def test_intact_bundle_launches(self):
        rc, state, launched = self.run_audit()
        self.assertTrue(launched)

    def test_tampered_artifact_never_launches(self):
        with (self.bundle / "diff.patch").open("a") as f:
            f.write("\n# tampered\n")
        rc, state, launched = self.run_audit()
        self.assertEqual((rc, state["status"], launched), (2, "rejected", False))
        self.assertIn("tampered: diff.patch", state["gate"]["reason"])

    def test_missing_artifact_never_launches(self):
        (self.bundle / "git-status.txt").unlink()
        rc, state, launched = self.run_audit()
        self.assertEqual((rc, launched), (2, False))
        self.assertIn("missing: git-status.txt", state["gate"]["reason"])

    def test_unhashed_manifest_never_launches(self):
        m = json.loads((self.bundle / "manifest.json").read_text())
        m.pop("artifact_sha256")
        m["version"] = 1
        (self.bundle / "manifest.json").write_text(json.dumps(m))
        rc, state, launched = self.run_audit()
        self.assertEqual((rc, launched), (2, False))

    def test_pruned_manifest_entry_never_launches(self):
        # Dropping an artifact from both disk and the hash map must not bypass the check.
        m = json.loads((self.bundle / "manifest.json").read_text())
        del m["artifact_sha256"]["git-status.txt"]
        (self.bundle / "manifest.json").write_text(json.dumps(m))
        (self.bundle / "git-status.txt").unlink()
        rc, state, launched = self.run_audit()
        self.assertEqual((rc, launched), (2, False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
