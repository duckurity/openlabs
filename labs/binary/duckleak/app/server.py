"""Serve the DuckLeak APK and nothing else."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APK = Path(__file__).with_name("duckleak.apk")
INDEX = (
    b"<!doctype html><title>NestGuard</title>"
    b"<h1>NestGuard</h1><p>DuckCorp internal build.</p>"
    b'<p><a href="/duckleak.apk">Download duckleak.apk</a></p>'
)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body, kind = INDEX, "text/html; charset=utf-8"
        elif self.path == "/duckleak.apk":
            body, kind = APK.read_bytes(), "application/vnd.android.package-archive"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
