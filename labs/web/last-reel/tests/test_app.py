"""Player routes, intended solve and accidental-disclosure regression tests."""
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / "app/__init__.py").is_file(), "The Flask application has not been implemented")
        application = importlib.import_module("app")
        from app.seed import initialize
        self.temp = tempfile.TemporaryDirectory(dir=os.getenv("LAST_REEL_TEST_TMP", str(ROOT.parent / "work")))
        self.addCleanup(self.temp.cleanup)
        self.path = initialize(Path(self.temp.name))
        self.client = application.create_app(self.path).test_client()

    def test_catalogue_and_search(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'data-film-card="true"'), 8)
        self.assertNotIn(b"duck{", response.data)
        response = self.client.get("/search", query_string={"q": "Platform"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Platform Nine", response.data)
        self.assertEqual(response.data.count(b'data-film-card="true"'), 1)
        response = self.client.get("/search", query_string={"q": "no-match-title"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No films found", response.data)

    def test_details_are_public_only(self):
        self.assertEqual(self.client.get("/films/1").status_code, 200)
        for path in ("/films/9", "/films/999", "/films/1%27%20OR%201=1", "/films/-1"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_intended_search_is_solvable(self):
        query = "' AND 1=0 UNION ALL SELECT 0,'Clearance',0,clearance_note,'record' FROM clearance_records -- "
        response = self.client.get("/search", query_string={"q": query})
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.get_data(as_text=True), r"duck\{[a-f0-9]{32}\}")

    def test_synthetic_markup_is_escaped(self):
        query = "' AND 1=0 UNION ALL SELECT 0,'<script>alert(1)</script>',0,'{{7*7}}','record' -- "
        response = self.client.get("/search", query_string={"q": query})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"<script>", response.data)
        self.assertIn(b"&lt;script&gt;", response.data)
        self.assertIn(b"{{7*7}}", response.data)

    def test_search_errors_are_safe_and_recoverable(self):
        for query in ("'", "x" * 513, "\x00", "' UNION SELECT 1 -- ", "'; DELETE FROM films; -- "):
            response = self.client.get("/search", query_string={"q": query})
            self.assertEqual(response.status_code, 400)
            self.assertIn(b"Search could not be completed", response.data)
            for marker in (b"Traceback", b"sqlite3", b"SELECT id,title", b"/opt/", b"duck{"):
                self.assertNotIn(marker, response.data)
        self.assertEqual(self.client.get("/search", query_string={"q": "Platform"}).status_code, 200)
        self.assertEqual(self.client.post("/search", data={"q": "Platform"}).status_code, 405)

    def test_duplicate_unknown_and_oversized_querystrings_are_rejected(self):
        for suffix in ("?q=a&q=b", "?q=a&unexpected=b", "?q=" + "x" * 2049):
            self.assertEqual(self.client.get("/search" + suffix).status_code, 400)

    def test_operator_data_and_maintainer_files_have_no_http_route(self):
        for path in ("/flag", "/debug", "/docs/official-solution.mdx", "/database/archive.sqlite", "/database/films.json", "/app/seed.py", "/digest.json", "/static/../database/schema.sql", "/.env", "/solver/solve.py"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404, path)
            self.assertNotIn(b"duck{", response.data)

    def test_security_headers_health_and_local_styles(self):
        response = self.client.get("/")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertIn("default-src 'none'", response.headers.get("Content-Security-Policy", ""))
        self.assertNotIn(b"https://", response.data)
        with self.client.get("/static/style.css") as styles:
            self.assertEqual(styles.status_code, 200)
        health = self.client.get("/health")
        self.assertEqual(health.json, {"service": "last-reel", "status": "ok"})
        self.assertNotIn(b"generation", health.data)


if __name__ == "__main__":
    unittest.main()
