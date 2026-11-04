"""HTTP-only evaluator solver regression tests."""
import importlib
import importlib.util
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class SolverTests(unittest.TestCase):
    def load_solver(self):
        path = ROOT / "solver/solve.py"
        self.assertTrue(path.is_file(), "The evaluator solver has not been implemented")
        spec = importlib.util.spec_from_file_location("last_reel_solver", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def rendered_client(self):
        application = importlib.import_module("app")
        from app.seed import initialize
        temp = tempfile.TemporaryDirectory(dir=os.getenv("LAST_REEL_TEST_TMP", str(ROOT.parent / "work")))
        self.addCleanup(temp.cleanup)
        return application.create_app(initialize(Path(temp.name))).test_client()

    def test_parser_preserves_escaped_record_text(self):
        solver = self.load_solver()
        records = solver.records('<article data-film-card="true"><h3>&lt;title&gt;</h3><p class="synopsis">CREATE TABLE clearance_records (clearance_note TEXT)</p></article>')
        self.assertEqual(records, [{"title": "<title>", "synopsis": "CREATE TABLE clearance_records (clearance_note TEXT)"}])

    def test_parser_reads_current_rendered_search_markup(self):
        solver = self.load_solver()
        client = self.rendered_client()
        public = client.get("/search", query_string={"q": "Platform"}).get_data(as_text=True)
        self.assertEqual([row["title"] for row in solver.records(public)], ["Platform Nine"])
        schema_query = "' AND 1=0 UNION ALL SELECT 0,name,0,sql,'schema' FROM sqlite_master WHERE type='table' -- "
        schema = client.get("/search", query_string={"q": schema_query}).get_data(as_text=True)
        self.assertIn("clearance_records", [row["title"] for row in solver.records(schema)])

    def test_solve_completes_against_rendered_application(self):
        solver = self.load_solver()
        client = self.rendered_client()

        def rendered_request(base, query):
            self.assertEqual(base, "http://127.0.0.1:8080")
            response = client.get("/search", query_string={"q": query})
            self.assertEqual(response.status_code, 200)
            return response.get_data(as_text=True)

        solver.request = rendered_request
        # Assert only the shape; never print or retain the runtime value.
        self.assertIsNotNone(re.fullmatch(r"duck\{[a-f0-9]{32}\}", solver.solve("http://127.0.0.1:8080")))

    def test_solver_targets_only_local_http(self):
        solver = self.load_solver()
        for url in ("http://127.0.0.1:8080", "http://localhost:8080"):
            self.assertEqual(solver.local_base(url), url)
        for url in ("https://example.com", "http://192.168.1.1:8080", "http://example.com", "file:///etc/passwd", "http://u:p@localhost:8080", "http://127.0.0.1:8080/path", "http://127.0.0.1:8080?other=1"):
            with self.assertRaises(ValueError):
                solver.local_base(url)


if __name__ == "__main__":
    unittest.main()
