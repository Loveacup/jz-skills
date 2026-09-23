#!/usr/bin/env python3
"""Permanent deterministic checks for process_probe classification (EXT-01).

Covers the contract cases: dead, alive, and query-error → unknown. Pure
classify() cases are fully deterministic; real-process cases use only the
current interpreter and an already-reaped child.
"""
import os
import subprocess
import unittest

import process_probe

ALIVE_ROW = "  123    1  123  123 Ss   launchd  Mon Sep 21 10:00:00 2026\n"
ZOMBIE_ROW = " 456    1  456  456 Z    defunct  Mon Sep 21 10:00:00 2026\n"


class ClassifyDeterministic(unittest.TestCase):
    def test_dead_requires_rc1_with_empty_stdout_and_empty_stderr(self):
        self.assertEqual(process_probe.classify(1, "", ""), "dead")
        self.assertEqual(process_probe.classify(1, "  \n", " \n"), "dead")

    def test_alive_single_supported_row(self):
        self.assertEqual(process_probe.classify(0, ALIVE_ROW, ""), "alive")

    def test_zombie_stat_is_not_alive_and_not_dead(self):
        self.assertEqual(process_probe.classify(0, ZOMBIE_ROW, ""), "zombie")

    def test_rc1_with_stderr_is_unknown_not_dead(self):
        self.assertEqual(
            process_probe.classify(1, "", "ps: illegal process id\n"), "unknown")

    def test_rc0_with_stderr_is_unknown(self):
        self.assertEqual(process_probe.classify(0, ALIVE_ROW, "warning\n"), "unknown")

    def test_other_nonzero_rc_is_unknown(self):
        for rc in (2, 70, 127, 255, -9):
            self.assertEqual(process_probe.classify(rc, "", ""), "unknown")
            self.assertEqual(process_probe.classify(rc, ALIVE_ROW, ""), "unknown")

    def test_unsupported_output_is_unknown(self):
        self.assertEqual(process_probe.classify(0, "", ""), "unknown")
        self.assertEqual(process_probe.classify(0, "garbage row\n", ""), "unknown")
        self.assertEqual(process_probe.classify(0, ALIVE_ROW + ZOMBIE_ROW, ""), "unknown")
        self.assertEqual(
            process_probe.classify(0, "  x    1  123  123 Ss   comm  now\n", ""), "unknown")

    def test_parse_identity_extracts_full_identity(self):
        identity = process_probe.parse_identity(ALIVE_ROW)
        self.assertEqual(identity["pid"], 123)
        self.assertEqual(identity["ppid"], 1)
        self.assertEqual(identity["pgid"], 123)
        self.assertEqual(identity["sid"], 123)
        self.assertEqual(identity["stat"], "Ss")
        self.assertEqual(identity["command"], "launchd")
        self.assertEqual(identity["start_time"], "Mon Sep 21 10:00:00 2026")


class ProbeRealProcess(unittest.TestCase):
    def test_alive_current_process(self):
        record = process_probe.probe(os.getpid())
        self.assertEqual(record["state"], "alive")
        self.assertEqual(record["exit_code"], 0)
        self.assertEqual(record["identity"]["pid"], os.getpid())
        self.assertGreater(record["identity"]["ppid"], 0)
        self.assertTrue(record["identity"]["start_time"])

    def test_dead_after_reaped_child(self):
        child = subprocess.Popen(["/bin/sleep", "0"])
        child.wait(timeout=10)
        record = process_probe.probe(child.pid)
        self.assertEqual(record["state"], "dead")
        self.assertEqual(record["exit_code"], 1)
        self.assertEqual(record["stdout"].strip(), "")
        self.assertEqual(record["stderr"].strip(), "")

    def test_query_error_is_unknown(self):
        record = process_probe.probe("not-a-pid")
        self.assertEqual(record["state"], "unknown")
        self.assertNotEqual(record["exit_code"], 0)
        self.assertTrue(record["stderr"].strip())


if __name__ == "__main__":
    unittest.main(verbosity=2)
