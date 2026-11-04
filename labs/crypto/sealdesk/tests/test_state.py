"""Runtime-only key, receipt, access-code, and flag generation tests."""

from __future__ import annotations

import hmac
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB_ROOT))

from app import state


class RuntimeStateTests(unittest.TestCase):
    def test_public_case_exposes_only_receipt_and_synthetic_case_metadata(self) -> None:
        first = state.generate_state()
        second = state.generate_state()
        public_text = json.dumps(first.public_case(), sort_keys=True)

        self.assertNotEqual(first.generation_id, second.generation_id)
        self.assertFalse(
            hmac.compare_digest(first.access_code, second.access_code),
            "Fresh state reused a recovery code.",
        )
        self.assertFalse(
            hmac.compare_digest(first.flag, second.flag),
            "Fresh state reused a flag.",
        )
        self.assertTrue(bool(re.fullmatch(r"[0-9a-f]{32}", first.access_code)))
        self.assertTrue(bool(re.fullmatch(r"duck\{[a-z0-9_]{16,40}\}", first.flag)))
        self.assertFalse(first.access_code in public_text, "Public case leaked the recovery code.")
        self.assertFalse(first.flag in public_text, "Public case leaked the flag.")
        self.assertEqual(set(first.public_case()), {
            "case_id", "document_id", "document_title", "sender", "recipient",
            "issued_on", "note", "receipt",
        })
        self.assertEqual(first.public_case()["receipt"], first.receipt)

    def test_runtime_state_representation_omits_private_values(self) -> None:
        instance = state.generate_state()
        sensitive = (
            instance.access_code,
            instance.flag,
            instance.encryption_key.hex(),
            instance.mac_key.hex(),
        )

        self.assertFalse(
            any(value in repr(instance) for value in sensitive),
            "RuntimeState representation exposed private runtime values.",
        )

    def test_initialization_is_idempotent_and_persists_only_inside_runtime_dir(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = state.initialize_state(Path(directory))
            state_path = Path(directory) / state.STATE_FILENAME
            original_bytes = state_path.read_bytes()
            again = state.initialize_state(Path(directory))

            self.assertEqual(first.generation_id, again.generation_id)
            self.assertEqual(state_path.read_bytes(), original_bytes)
            self.assertEqual(state_path.parent, Path(directory))
            if os.name != "nt":
                self.assertEqual(state_path.stat().st_mode & 0o777, 0o600)

    def test_flag_hash_cli_outputs_only_the_checker_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            expected = state.initialize_state(Path(directory)).flag_hash
            environment = os.environ.copy()
            environment["SEALDESK_STATE_DIR"] = directory
            result = subprocess.run(
                [
                    sys.executable, "-B", "-c",
                    "from app.state import main; raise SystemExit(main())",
                    "--flag-hash-json",
                ],
                cwd=LAB_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
                check=False,
            )

        self.assertEqual(result.returncode, 0, "The runtime digest command failed.")
        self.assertEqual(json.loads(result.stdout), {"flag_hash": expected})
        self.assertEqual(result.stderr, "")

    def test_schema_version_rejects_boolean_true(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            instance = state.generate_state()
            payload = instance.private_payload()
            payload["schema_version"] = True
            state_path = Path(directory) / state.STATE_FILENAME
            state_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValueError):
                state.load_state(state_path)

    def test_private_state_rejects_access_code_mismatch_with_authenticated_receipt(self) -> None:
        instance = state.generate_state()
        payload = instance.private_payload()
        payload["access_code"] = "0" * 32 if instance.access_code != "0" * 32 else "1" * 32

        with self.assertRaises(ValueError):
            state._state_from_payload(payload)

    def test_invalid_or_tampered_runtime_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / state.STATE_FILENAME
            state_path.write_text(json.dumps({"unexpected": "value"}), encoding="utf-8")

            with self.assertRaises(ValueError):
                state.load_state(state_path)


if __name__ == "__main__":
    unittest.main()
