"""Operator metadata synchronization regression tests."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OperatorTests(unittest.TestCase):
    def load_control(self):
        path = ROOT / "scripts/control.py"
        self.assertTrue(path.is_file(), "Operator controls have not been implemented")
        spec = importlib.util.spec_from_file_location("last_reel_control", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_metadata_update_is_exact_and_idempotent(self):
        control = self.load_control()
        with tempfile.TemporaryDirectory(dir=os.getenv("LAST_REEL_TEST_TMP", str(ROOT.parent / "work"))) as directory:
            path = Path(directory) / "lab.yml"
            original = "# retained comment\nname: last-reel\nflag_hash: " + "0" * 64 + "\nstatus: experimental\n"
            path.write_text(original)
            value = {"generation_id": "a" * 32, "flag_hash": "b" * 64}
            self.assertTrue(control.update_metadata(path, value))
            self.assertEqual(path.read_text(), original.replace("0" * 64, "b" * 64))
            self.assertFalse(control.update_metadata(path, value))

    def test_malformed_state_and_duplicate_hashes_fail_without_writes(self):
        control = self.load_control()
        with tempfile.TemporaryDirectory(dir=os.getenv("LAST_REEL_TEST_TMP", str(ROOT.parent / "work"))) as directory:
            path = Path(directory) / "lab.yml"
            original = "flag_hash: " + "0" * 64 + "\nflag_hash: " + "0" * 64 + "\n"
            path.write_text(original)
            for state in ({"generation_id": "a" * 32, "flag_hash": "b" * 64}, {"flag_hash": "not-a-hash"}, {"generation_id": "a" * 32, "flag_hash": "b" * 64, "flag": "synthetic-invalid"}):
                with self.assertRaises(ValueError):
                    control.update_metadata(path, state)
                self.assertEqual(path.read_text(), original)


if __name__ == "__main__":
    unittest.main()
