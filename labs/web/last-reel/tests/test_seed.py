"""Seed and flag lifecycle regression tests; no real flags are printed."""
import importlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class SeedTests(unittest.TestCase):
    def test_initialization_exposes_eight_public_films_and_digest_only_operator_state(self):
        self.assertTrue((ROOT / "app/seed.py").is_file(), "The seed initializer has not been implemented")
        seed = importlib.import_module("app.seed")
        with tempfile.TemporaryDirectory(dir=os.getenv("LAST_REEL_TEST_TMP", str(ROOT.parent / "work"))) as directory:
            path = seed.initialize(Path(directory))
            with closing(sqlite3.connect(path)) as reader:
                self.assertEqual(reader.execute("SELECT count(*) FROM films WHERE is_public=1").fetchone()[0], 8)
                self.assertEqual(reader.execute("SELECT count(*) FROM films").fetchone()[0], 9)
                note = reader.execute("SELECT clearance_note FROM clearance_records").fetchone()[0]
                self.assertEqual(len(re.findall(r"duck\{[a-f0-9]{32}\}", note)), 1)
                self.assertFalse(any("duck{" in str(row) for row in reader.execute("SELECT * FROM films")))
            state = seed.digest(Path(directory))
            self.assertEqual(set(state), {"generation_id", "flag_hash"})
            self.assertRegex(state["flag_hash"], r"^[a-f0-9]{64}$")
            self.assertNotIn("duck{", json.dumps(state))


if __name__ == "__main__":
    unittest.main()
