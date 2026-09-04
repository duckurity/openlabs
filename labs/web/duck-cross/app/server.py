"""duck-cross reports portal."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8377
REPORTS = json.loads((Path(__file__).parent / "data" / "reports.json").read_text(encoding="utf-8"))

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>duck cross</title>
<style>
  :root { color-scheme: dark; }
  body {
    margin: 0;
    padding: 3rem 1.5rem;
    background: #1c1916;
    color: #d6cfc7;
    font: 15px/1.6 ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }
  main { max-width: 34rem; margin: 0 auto; }
  h1 { font-size: 1.25rem; font-weight: 600; margin: 0 0 0.25rem; color: #f2ede7; }
  p.sub { margin: 0 0 2rem; color: #8a8078; }
  .eyebrow {
    font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase;
    color: #8a8078; margin: 0 0 0.75rem;
  }
  ul { list-style: none; padding: 0; margin: 0; }
  li { border-bottom: 1px solid #322c26; }
  li:last-child { border-bottom: none; }
  button {
    width: 100%; display: flex; justify-content: space-between; align-items: center;
    padding: 0.7rem 0.25rem; background: none; border: none; cursor: pointer;
    color: #d6cfc7; font: inherit; text-align: left;
  }
  button:hover, button:focus-visible { color: #f2ede7; }
  button .id { color: #8a8078; }
  pre {
    margin-top: 2rem; padding: 1rem; background: #14110e;
    border: 1px solid #322c26; color: #e8e2da; overflow-x: auto;
  }
</style>
</head>
<body>
<main>
  <h1>duck cross</h1>
  <p class="sub">crossing reports, filed by wardens</p>
  <p class="eyebrow">public reports</p>
  <ul>
    <li><button data-id="1"><span>mill lane</span><span class="id">01</span></button></li>
    <li><button data-id="2"><span>orchard row</span><span class="id">02</span></button></li>
    <li><button data-id="3"><span>stone bridge</span><span class="id">03</span></button></li>
    <li><button data-id="4"><span>rail crossing</span><span class="id">04</span></button></li>
    <li><button data-id="5"><span>harbor road</span><span class="id">05</span></button></li>
  </ul>
  <pre id="readout" hidden></pre>
</main>
<script>
  const readout = document.getElementById("readout");
  for (const button of document.querySelectorAll("button[data-id]")) {
    button.addEventListener("click", async () => {
      const response = await fetch("/api/reports/" + button.dataset.id);
      const report = await response.json();
      readout.hidden = false;
      readout.textContent = JSON.stringify(report, null, 2);
    });
  }
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return

        if self.path.startswith("/api/reports/"):
            raw = self.path.removeprefix("/api/reports/").split("?")[0]
            report = None
            if raw.isdigit():
                report = REPORTS.get(str(int(raw)))
            if report is None:
                body = json.dumps({"error": "report not found"}).encode("utf-8")
                self._send(404, body, "application/json")
                return
            body = json.dumps(report, indent=2).encode("utf-8")
            self._send(200, body, "application/json")
            return

        self._send(404, b"not found", "text/plain; charset=utf-8")

    def log_message(self, format: str, *args) -> None:
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"duck cross listening on {PORT}")
    server.serve_forever()
