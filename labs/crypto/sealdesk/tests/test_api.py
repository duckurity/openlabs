"""Black-box API tests for public case delivery and separate document access."""

from __future__ import annotations

import base64
import copy
import hmac
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app, state


def encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class SealDeskApiTests(unittest.TestCase):
    def assert_secret_absent(self, secret: str, content: str) -> None:
        self.assertFalse(
            secret in content,
            "A response included private or solution-revealing text.",
        )

    def setUp(self) -> None:
        self.assertIsNotNone(create_app, "app.create_app must expose the HTTP contract")
        self.runtime = state.generate_state()
        application = create_app({"TESTING": True, "RUNTIME_STATE": self.runtime})
        self.client = application.test_client()

    def test_health_is_constant_and_does_not_depend_on_secrets(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"service": "sealdesk", "status": "ok"})

    def test_case_endpoint_returns_the_receipt_but_no_recovery_material(self) -> None:
        response = self.client.get("/case")
        body = response.get_json()
        encoded = json.dumps(body, sort_keys=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["document_id"], self.runtime.document_id)
        self.assertEqual(set(body["receipt"]), {"version", "iv", "ciphertext", "tag"})
        self.assert_secret_absent(self.runtime.access_code, encoded)
        self.assert_secret_absent(self.runtime.flag, encoded)
        self.assert_secret_absent(encode(self.runtime.encryption_key), encoded)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_check_endpoint_uses_two_fixed_failure_classes_and_never_echoes_input(self) -> None:
        damaged = copy.deepcopy(self.runtime.receipt)
        ciphertext = bytearray(decode(damaged["ciphertext"]))
        ciphertext[-17] ^= 1
        damaged["ciphertext"] = encode(bytes(ciphertext))
        damaged["tag"] = encode(b"X" * 32)
        untrusted = copy.deepcopy(self.runtime.receipt)
        untrusted["tag"] = encode(b"X" * 32)

        bad_padding_response = self.client.post("/api/receipts/check", json=damaged)
        bad_mac_response = self.client.post("/api/receipts/check", json=untrusted)

        self.assertEqual(bad_padding_response.status_code, 422)
        self.assertEqual(bad_padding_response.get_json(), {
            "status": "damaged_envelope", "message": "Receipt could not be decoded."
        })
        self.assertEqual(bad_mac_response.status_code, 422)
        self.assertEqual(bad_mac_response.get_json(), {
            "status": "untrusted_envelope", "message": "Receipt could not be trusted."
        })
        self.assert_secret_absent(self.runtime.access_code, bad_padding_response.get_data(as_text=True))
        self.assert_secret_absent(self.runtime.access_code, bad_mac_response.get_data(as_text=True))

    def test_well_formed_untrusted_receipt_is_not_accepted_or_disclosed(self) -> None:
        response = self.client.post("/api/receipts/check", json=self.runtime.receipt)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            "status": "valid_receipt",
            "message": "Receipt accepted. The document can be opened separately.",
        })
        self.assert_secret_absent(self.runtime.access_code, response.get_data(as_text=True))
        self.assert_secret_absent(self.runtime.flag, response.get_data(as_text=True))

    def test_document_open_requires_exact_server_side_code_and_document_id(self) -> None:
        wrong_code = "0" * 32 if self.runtime.access_code != "0" * 32 else "1" * 32
        wrong_responses = [
            self.client.post("/api/documents/open", json={
                "document_id": self.runtime.document_id, "access_code": wrong_code,
            }),
            self.client.post("/api/documents/open", json={
                "document_id": "CASE-0000", "access_code": self.runtime.access_code,
            }),
            self.client.post("/api/documents/open", json={"receipt": self.runtime.receipt}),
        ]

        for response in wrong_responses:
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.get_json(), {
                "status": "document_unavailable", "message": "The document could not be opened."
            })

        success = self.client.post("/api/documents/open", json={
            "document_id": self.runtime.document_id,
            "access_code": self.runtime.access_code,
        })
        self.assertEqual(success.status_code, 200)
        self.assertEqual(success.get_json()["status"], "document_opened")
        self.assertTrue(
            hmac.compare_digest(success.get_json()["flag"], self.runtime.flag),
            "The accepted document response contained the wrong flag.",
        )
        self.assert_secret_absent(self.runtime.access_code, success.get_data(as_text=True))

    def test_document_open_rejects_non_ascii_identifier_with_fixed_response(self) -> None:
        response = self.client.post(
            "/api/documents/open",
            data=b'{"document_id":"\\ud800","access_code":"00000000000000000000000000000000"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json(), {
            "status": "document_unavailable", "message": "The document could not be opened."
        })

    def test_player_page_has_safe_live_targets_for_the_opened_document(self) -> None:
        markup = self.client.get("/").get_data(as_text=True)
        with self.client.get("/static/workbench.js") as script_response:
            script = script_response.get_data(as_text=True)

            self.assertEqual(script_response.status_code, 200)
            self.assertIn('id="document-output"', markup)
            self.assertIn('id="document-title"', markup)
            self.assertIn('id="document-text"', markup)
            self.assertIn("documentTitle.textContent", script)
            self.assertIn("documentText.textContent", script)
            self.assertIn('body.status === "valid_receipt"', script)
            self.assertNotIn("innerHTML", script)

    def test_player_page_is_a_workbench_not_a_solution_page(self) -> None:
        response = self.client.get("/")
        body = response.get_data(as_text=True).lower()

        self.assertEqual(response.status_code, 200)
        self.assertIn("sealdesk", body)
        self.assertIn("check receipt", body)
        self.assertIn("open document", body)
        self.assert_secret_absent("padding oracle", body)
        self.assert_secret_absent(self.runtime.access_code, body)
        self.assert_secret_absent(self.runtime.flag, body)

    def test_oversized_api_requests_receive_one_fixed_bounded_error(self) -> None:
        payload = {"value": "x" * 9000}
        responses = [
            self.client.post("/api/receipts/check", json=payload),
            self.client.post("/api/documents/open", json=payload),
        ]

        for response in responses:
            self.assertEqual(response.status_code, 413)
            self.assertEqual(response.get_json(), {
                "status": "request_too_large", "message": "Request is too large."
            })

    def test_deeply_nested_json_requests_return_fixed_bounded_errors(self) -> None:
        payload = b"[" * 1100 + b"0" + b"]" * 1100
        self.assertLess(len(payload), 8192)
        cases = (
            ("/api/receipts/check", 400, {
                "status": "invalid_receipt", "message": "Receipt is not in the expected format."
            }),
            ("/api/documents/open", 403, {
                "status": "document_unavailable", "message": "The document could not be opened."
            }),
        )

        for path, status, body in cases:
            with self.subTest(path=path):
                response = self.client.post(path, data=payload, content_type="application/json")
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.get_json(), body)

    def test_malformed_json_has_a_fixed_response(self) -> None:
        response = self.client.post(
            "/api/receipts/check", data=b"not-json", content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {
            "status": "invalid_receipt", "message": "Receipt is not in the expected format."
        })


if __name__ == "__main__":
    unittest.main()
