#!/usr/bin/env python3
"""Permanent deterministic regression coverage for every rejected probe case."""
import os
import subprocess
import unittest
from unittest.mock import patch
import process_probe as p

ROW = "123 1 123 Ss Mon Sep 21 10:00:00 2026 /very/long/executable --argument with spaces\n"
ZOMBIE = ROW.replace(" Ss ", " Z ")


class Classification(unittest.TestCase):
    def test_only_literal_empty_rc1_is_dead(self):
        self.assertEqual(p.classify(1, "", ""), "dead")
        for out, err in [(" ", ""), ("\n", ""), ("", " "), ("", "\n"), (" \n", " \n"), ("", "error")]:
            with self.subTest(out=out, err=err):
                self.assertEqual(p.classify(1, out, err), "unknown")

    def test_alive_and_distinct_zombie(self):
        self.assertEqual(p.classify(0, ROW, ""), "alive")
        self.assertEqual(p.classify(0, ZOMBIE, ""), "zombie")

    def test_any_stderr_or_other_nonzero(self):
        for rc in (0, 1, 2, 70, 127, 255, -9):
            for err in (" ", "\n", "warning"):
                self.assertEqual(p.classify(rc, ROW, err), "unknown")
        for rc in (2, 70, 127, 255, -9):
            for out in ("", ROW):
                self.assertEqual(p.classify(rc, out, ""), "unknown")

    def test_invalid_stat_and_start_time(self):
        for state in ("INVALID", "Q", "S?", "ZZ", "X", "s"):
            self.assertEqual(p.classify(0, ROW.replace("Ss", state), ""), "unknown")
        for date in ("garbage", "Mon Sep 31 10:00:00 2026", "Mon Sep 21 25:00:00 2026",
                     "Tue Sep 21 10:00:00 2026", "Mon Xxx 21 10:00:00 2026", "Mon Sep 21 10:00:60 2026"):
            self.assertEqual(p.classify(0, ROW.replace("Mon Sep 21 10:00:00 2026", date), ""), "unknown")
        self.assertEqual(p.classify(0, "1 2 3 4 INVALID comm garbage", ""), "unknown")

    def test_malformed_rows(self):
        for row in ("", "garbage", ROW + ROW, "\n" + ROW, ROW.replace("123", "x", 1),
                    ROW.replace("123", "0", 1), ROW.replace("123", "-1", 1),
                    "123 1 123 S Mon Sep 21 10:00:00 2026", ROW + "extra\n"):
            self.assertEqual(p.classify(0, row, ""), "unknown")

    def test_full_command(self):
        command = "/long/path/python3 " + "argument " * 100
        row = ROW[:ROW.index('/very')] + command + "\n"
        self.assertEqual(p.parse_identity(row)["command"], command.rstrip())
        self.assertEqual(p.parse_identity(ROW)["start_time"], "Mon Sep 21 10:00:00 2026")


class Queries(unittest.TestCase):
    def result(self, row=ROW, rc=0, err=""):
        return subprocess.CompletedProcess([], rc, row, err)

    def test_darwin_numeric_sid_and_unlimited_command(self):
        with patch.object(p.subprocess, 'run', return_value=self.result()) as run, patch.object(p.os, 'getsid', return_value=123):
            record = p.probe(123)
        self.assertEqual(record['state'], 'alive')
        self.assertEqual(record['identity']['sid'], 123)
        argv = run.call_args.args[0]
        self.assertIn('-ww', argv)
        self.assertNotIn('sess=', p.PS_FORMAT)
        self.assertTrue(p.PS_FORMAT.endswith('command='))
        self.assertEqual(run.call_args.kwargs['env']['LC_ALL'], 'C')
        self.assertEqual(run.call_count, 2)

    def test_missing_executable_and_all_query_exceptions(self):
        for exc in (FileNotFoundError(), PermissionError(), OSError(), ValueError(),
                    UnicodeDecodeError('utf8', b'\xff', 0, 1, 'bad'), RuntimeError()):
            with patch.object(p.subprocess, 'run', side_effect=exc):
                self.assertEqual(p.probe(123)['state'], 'unknown')

    def test_timeout_is_unknown_json_safe(self):
        with patch.object(p.subprocess, 'run', side_effect=subprocess.TimeoutExpired('ps', 1, output=b'partial', stderr=b' ')):
            result = p.probe(123)
        self.assertEqual(result['state'], 'unknown')
        self.assertEqual(result['stdout'], 'partial')
        self.assertEqual(result['stderr'], ' ')

    def test_sid_errors_are_unknown_not_dead(self):
        for exc in (ProcessLookupError(), PermissionError()):
            with patch.object(p.subprocess, 'run', return_value=self.result()), patch.object(p.os, 'getsid', side_effect=exc):
                self.assertEqual(p.probe(123)['state'], 'unknown')

    def test_identity_race_and_second_query_error(self):
        for second in (self.result(rc=1, row=''), self.result(err=' '), self.result(row=ROW.replace('10:00:00', '10:00:01'))):
            with patch.object(p.subprocess, 'run', side_effect=[self.result(), second]), patch.object(p.os, 'getsid', return_value=123):
                self.assertEqual(p.probe(123)['state'], 'unknown')
        with patch.object(p.subprocess, 'run', return_value=self.result()), patch.object(p.os, 'getsid', side_effect=[123, 456]):
            self.assertEqual(p.probe(123)['state'], 'unknown')

    def test_wrong_pid_invalid_sid_and_pid(self):
        with patch.object(p.subprocess, 'run', return_value=self.result()):
            self.assertEqual(p.probe(456)['state'], 'unknown')
            with patch.object(p.os, 'getsid', return_value=0):
                self.assertEqual(p.probe(123)['state'], 'unknown')
        for pid in ('not-a-pid', '1,2', -1, 0, True):
            self.assertEqual(p.probe(pid)['state'], 'unknown')

    def test_mock_dead_and_zombie(self):
        with patch.object(p.subprocess, 'run', return_value=self.result(row='', rc=1)):
            self.assertEqual(p.probe(123)['state'], 'dead')
        with patch.object(p.subprocess, 'run', return_value=self.result(row=ZOMBIE)), patch.object(p.os, 'getsid', return_value=123):
            self.assertEqual(p.probe(123)['state'], 'zombie')


class LiveProbe(unittest.TestCase):
    def test_current_process_and_native_sid(self):
        result = p.probe(os.getpid())
        self.assertEqual(result['state'], 'alive', result)
        self.assertEqual(result['identity']['sid'], os.getsid(0))
        self.assertEqual(result['identity']['pgid'], os.getpgrp())

    def test_reaped_child(self):
        child = subprocess.Popen(['/bin/sleep', '0'])
        child.wait(timeout=10)
        result = p.probe(child.pid)
        self.assertEqual(result['state'], 'dead', result)
        self.assertEqual((result['stdout'], result['stderr']), ('', ''))


if __name__ == '__main__':
    unittest.main(verbosity=2)
