"""Reference attack tests use the rendered page and the live Flask route contract."""

from __future__ import annotations

import hmac
import sys
import threading
import unittest
from pathlib import Path

from werkzeug.serving import WSGIRequestHandler, make_server

LAB_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB_ROOT))

from app import create_app, state
from solver import solve


class _QuietRequestHandler(WSGIRequestHandler):
    def log(self, _kind: str, _message: str, *_args: object) -> None:
        return


class ReferenceSolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNotNone(create_app, "Flask app factory is required for solver tests")
        self.assertIsNotNone(solve, "solver.solve must implement the reference attack")
        self.runtime = state.generate_state()
        self.application = create_app({"TESTING": True, "RUNTIME_STATE": self.runtime})
        self.client = self.application.test_client()

    def test_solver_reads_the_receipt_from_the_actual_rendered_workbench(self) -> None:
        markup = self.client.get("/").get_data(as_text=True)
        receipt = solve.extract_receipt_from_html(markup)

        self.assertEqual(receipt, self.runtime.receipt)

    def test_padding_oracle_recovers_the_code_and_separate_open_returns_the_flag(self) -> None:
        case = self.client.get("/case").get_json()

        def oracle(probe: dict[str, str]) -> bool:
            response = self.client.post("/api/receipts/check", json=probe)
            status = response.get_json()["status"]
            if status in {"untrusted_envelope", "valid_receipt"}:
                return True
            if status == "damaged_envelope":
                return False
            raise solve.SolveError("The receipt service rejected a well-formed oracle probe.")

        access_code = solve.recover_access_code(case["receipt"], oracle, case["document_id"])
        opened = self.client.post("/api/documents/open", json={
            "document_id": case["document_id"], "access_code": access_code,
        })

        self.assertTrue(
            hmac.compare_digest(access_code, self.runtime.access_code),
            "The solver recovered the wrong access code.",
        )
        self.assertEqual(opened.status_code, 200)
        self.assertTrue(
            hmac.compare_digest(opened.get_json()["flag"], self.runtime.flag),
            "The opened document returned the wrong flag.",
        )

    def test_http_solver_uses_the_local_workbench_and_opens_the_separate_document(self) -> None:
        server = make_server(
            "127.0.0.1", 8080, self.application, request_handler=_QuietRequestHandler
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = solve.solve_http("http://127.0.0.1:8080")
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.assertFalse(thread.is_alive(), "The test-only local server did not stop cleanly.")
        self.assertTrue(
            hmac.compare_digest(result.access_code, self.runtime.access_code),
            "The HTTP solver recovered the wrong access code.",
        )
        self.assertTrue(
            hmac.compare_digest(result.flag, self.runtime.flag),
            "The HTTP solver returned the wrong accepted flag.",
        )

    def test_solver_rejects_unexpected_oracle_responses_and_nonlocal_origins(self) -> None:
        receipt = self.runtime.receipt
        with self.assertRaises(solve.SolveError):
            solve.recover_access_code(receipt, lambda _probe: None, self.runtime.document_id)
        for address in (
            "https://127.0.0.1:8080",
            "http://example.invalid:8080",
            "http://127.0.0.1:9000",
            "http://user@127.0.0.1:8080",
        ):
            with self.subTest(address=address):
                with self.assertRaises(solve.SolveError):
                    solve.validate_base_url(address)
        self.assertEqual(solve.validate_base_url("http://127.0.0.1:8080"), "http://127.0.0.1:8080")


if __name__ == "__main__":
    unittest.main()
