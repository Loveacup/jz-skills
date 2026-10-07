"""Regression tests using an isolated SQLite database, never live history."""
import importlib.util
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collector-daemon.py"
spec = importlib.util.spec_from_file_location("collector", SCRIPT)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class CleanupOldTests(unittest.TestCase):
    def test_deletion_is_committed_before_vacuum_and_recent_survives(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.db"
            with closing(sqlite3.connect(path)) as conn:
                conn.execute("CREATE TABLE snapshots (timestamp TEXT)")
                recent = datetime.now().isoformat()
                conn.executemany("INSERT INTO snapshots VALUES (?)", [
                    ((datetime.now() - timedelta(days=120)).isoformat(),),
                    (recent,),
                ])
                conn.commit()
                self.assertEqual(collector.cleanup_old(conn, 90), 1)
                self.assertFalse(conn.in_transaction)
                with closing(sqlite3.connect(path)) as reader:
                    self.assertEqual(reader.execute("SELECT timestamp FROM snapshots").fetchall(), [(recent,)])
                    self.assertEqual(reader.execute("PRAGMA quick_check").fetchone()[0], "ok")

    def test_no_deletions_does_not_vacuum_or_leave_transaction(self):
        with closing(sqlite3.connect(":memory:")) as conn:
            conn.execute("CREATE TABLE snapshots (timestamp TEXT)")
            queries = []
            conn.set_trace_callback(queries.append)
            self.assertEqual(collector.cleanup_old(conn, 90), 0)
            self.assertFalse(conn.in_transaction)
            self.assertFalse(any(q.upper().startswith("VACUUM") for q in queries))

    def test_does_not_commit_callers_transaction(self):
        with closing(sqlite3.connect(":memory:")) as conn:
            conn.execute("CREATE TABLE snapshots (timestamp TEXT)")
            conn.execute("INSERT INTO snapshots VALUES (?)", (datetime.now().isoformat(),))
            with self.assertRaisesRegex(sqlite3.ProgrammingError, "idle connection"):
                collector.cleanup_old(conn, 90)
            self.assertTrue(conn.in_transaction)
            conn.rollback()
            self.assertEqual(conn.execute("SELECT count(*) FROM snapshots").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
