"""Read-only SQL safety and intended vulnerability regression tests."""
import hashlib
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / "app/db.py").is_file(), "The guarded SQL layer has not been implemented")
        self.db = importlib.import_module("app.db")
        from app.seed import initialize
        self.temp = tempfile.TemporaryDirectory(dir=os.getenv("LAST_REEL_TEST_TMP", str(ROOT.parent / "work")))
        self.addCleanup(self.temp.cleanup)
        self.path = initialize(Path(self.temp.name))
        self.before = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def tearDown(self):
        if hasattr(self, "path"):
            self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), self.before)

    def test_normal_search_is_public_only(self):
        rows = self.db.search(self.path, "")
        self.assertEqual(len(rows), 8)
        self.assertEqual(self.db.search(self.path, "Platform")[0]["title"], "Platform Nine")
        self.assertEqual(self.db.search(self.path, "Last Reel"), [])

    def test_union_can_read_schema_then_clearance(self):
        rows = self.db.search(self.path, "' AND 1=0 UNION ALL SELECT 0,name,0,sql,'schema' FROM sqlite_master WHERE type='table' -- ")
        names = {row["title"] for row in rows}
        self.assertEqual(names, {"films", "clearance_records"})
        rows = self.db.search(self.path, "' AND 1=0 UNION ALL SELECT 0,'Clearance',0,clearance_note,'record' FROM clearance_records -- ")
        self.assertRegex(rows[0]["synopsis"], r"duck\{[a-f0-9]{32}\}")

    def test_hidden_metadata_is_not_the_flag(self):
        rows = self.db.search(self.path, "' OR 1=1 -- ")
        self.assertEqual(len(rows), 9)
        self.assertFalse(any("duck{" in str(row) for row in rows))

    def test_writes_and_configuration_are_denied(self):
        for sql in ("DELETE FROM films", "CREATE TABLE forbidden(x)", "ATTACH ':memory:' AS extra", "PRAGMA writable_schema=ON", "SELECT load_extension('/tmp/not-a-library')", "SELECT randomblob(1000000)"):
            with self.subTest(sql=sql):
                with self.assertRaises(self.db.QueryRejected):
                    self.db.execute(self.path, sql)

    def test_multiple_statements_and_wrong_column_counts_are_rejected(self):
        for query in ("'; DELETE FROM films; -- ", "' UNION SELECT 1 -- "):
            with self.subTest(query=query):
                with self.assertRaises(self.db.QueryRejected):
                    self.db.search(self.path, query)

    def test_user_input_is_bounded(self):
        for query in ("x" * 513, "abc\x00def"):
            with self.assertRaises(self.db.QueryRejected):
                self.db.search(self.path, query)

    def test_query_budget_interrupts_bounded_cross_join(self):
        with self.assertRaises(self.db.QueryRejected):
            self.db.execute(self.path, "SELECT count(*) FROM films a,films b,films c,films d,films e,films f", max_vm_steps=1000)

    def test_rows_and_cells_are_bounded(self):
        rows = self.db.execute(self.path, "SELECT a.title FROM films a,films b,films c")
        self.assertEqual(len(rows), 24)
        with self.assertRaises(self.db.QueryRejected):
            self.db.execute(self.path, "SELECT ?", ("x" * 4097,))

    def test_parameterized_details_do_not_expose_private_films(self):
        self.assertEqual(self.db.film(self.path, 1)["title"], "Platform Nine")
        self.assertIsNone(self.db.film(self.path, 9))
        self.assertIsNone(self.db.film(self.path, 999))


if __name__ == "__main__":
    unittest.main()
