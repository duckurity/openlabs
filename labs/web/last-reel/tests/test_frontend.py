"""Archive presentation and native browsing regression tests."""
import os
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from app.seed import initialize


class Links(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.links = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs))


class FrontendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.getenv("LAST_REEL_TEST_TMP", str(ROOT.parent / "work")))
        self.addCleanup(self.temp.cleanup)
        self.client = create_app(initialize(Path(self.temp.name))).test_client()

    def test_search_feedback_precedes_homepage_introduction(self):
        home = self.client.get("/").get_data(as_text=True)
        self.assertIn("Some stories deserve", home)
        for query in ("Platform", "no-match-title"):
            result = self.client.get("/search", query_string={"q": query})
            self.assertEqual(result.status_code, 200)
            self.assertNotIn("Some stories deserve", result.get_data(as_text=True))
        self.assertIn("1 record returned", self.client.get("/search?q=Platform").get_data(as_text=True))

    def test_record_roundtrip_preserves_local_search_context(self):
        results = self.client.get("/search?q=Platform").get_data(as_text=True)
        links = [link for link in Links(results).links if link.get("class") == "film-record-link"]
        self.assertEqual(len(links), 1, "The complete film card should be a single native link")
        record = links[0]
        self.assertTrue(record.get("aria-labelledby"))
        address = urlsplit(record["href"])
        self.assertEqual(address.path, "/films/1")
        self.assertEqual(parse_qs(address.query), {"q": ["Platform"]})
        detail = self.client.get(record["href"]).get_data(as_text=True)
        returns = [link["href"] for link in Links(detail).links if urlsplit(link["href"]).path == "/search"]
        self.assertEqual(len(returns), 1)
        self.assertEqual(parse_qs(urlsplit(returns[0]).query), {"q": ["Platform"]})
        self.assertIn("Back to search results", detail)

    def test_archive_copy_describes_records_not_playback(self):
        markup = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("AVAILABLE FOR PUBLIC VIEWING", markup)
        self.assertIn("Public archive records", markup)
        self.assertIn("No viewing files are hosted here", markup)
        self.assertIn("release-clearance review", markup)

    def test_control_styles_supply_accessible_interaction_states(self):
        markup = self.client.get("/").get_data(as_text=True)
        sheets = []
        for address in re.findall(r'href="([^\"]+\.css)"', markup):
            with self.client.get(address) as response:
                self.assertEqual(response.status_code, 200)
                sheets.append(response.get_data(as_text=True))
        styles = "\n".join(sheets)
        colors = dict(re.findall(r"--([a-z-]+)\s*:\s*(#[a-fA-F0-9]{6})", styles))

        def contrast(first, second):
            def luminance(color):
                channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
                linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
                return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
            lower, upper = sorted((luminance(first), luminance(second)))
            return (upper + 0.05) / (lower + 0.05)

        self.assertGreaterEqual(contrast(colors["accent"], colors["paper"]), 3)
        self.assertGreaterEqual(contrast(colors.get("control-line", colors["line"]), colors["paper"]), 3)
        self.assertGreaterEqual(contrast(colors["muted"], colors.get("surface", "#faf8f3")), 4.5)
        self.assertRegex(styles, r"input::placeholder\s*\{[^}]*color:\s*var\(--muted\)")
        self.assertIn(".film-record-link:focus-visible", styles)
        self.assertIn("prefers-reduced-motion: reduce", styles)
        self.assertNotIn("<script", markup)

    def test_return_context_never_selects_an_external_destination(self):
        query = '//external.invalid/?q="<script>"&next=/outside'
        detail = self.client.get("/films/1", query_string={"q": query}).get_data(as_text=True)
        links = [link["href"] for link in Links(detail).links]
        for address in links:
            parsed = urlsplit(address)
            self.assertEqual(parsed.scheme, "")
            self.assertEqual(parsed.netloc, "")
        search = next(address for address in links if urlsplit(address).path == "/search")
        self.assertEqual(parse_qs(urlsplit(search).query), {"q": [query]})
        self.assertNotIn("<script>", detail)
        for arguments in ({"q": "x" * 513}, {"q": "\x00"}, [("q", "a"), ("q", "b")], {"return": "//external.invalid/"}):
            markup = self.client.get("/films/1", query_string=arguments).get_data(as_text=True)
            self.assertIn("Back to the collection", markup)
            self.assertFalse(any(urlsplit(link["href"]).path == "/search" for link in Links(markup).links))

    def test_home_record_cards_have_distinct_accessible_names(self):
        markup = self.client.get("/").get_data(as_text=True)
        links = [link for link in Links(markup).links if link.get("class") == "film-record-link"]
        self.assertEqual(len(links), 8)
        names = {link["aria-labelledby"] for link in links}
        self.assertEqual(len(names), 8)
        for link in links:
            self.assertIn('id="' + link["aria-labelledby"] + '"', markup)
            self.assertEqual(urlsplit(link["href"]).query, "")

    def test_synthetic_results_do_not_gain_public_record_links(self):
        query = "' AND 1=0 UNION ALL SELECT 0,'Synthetic record',0,'A search result','record' -- "
        response = self.client.get("/search", query_string={"q": query})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Synthetic record", response.get_data(as_text=True))
        self.assertFalse(any(link.get("class") == "film-record-link" for link in Links(response.get_data(as_text=True)).links))


if __name__ == "__main__":
    unittest.main()
