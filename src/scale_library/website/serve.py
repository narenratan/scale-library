"""Serve the site/ directory locally with CORS headers on JSON files."""

import functools
import http.server
import sys


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        if self.path.endswith(".json"):
            self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    handler = functools.partial(Handler, directory="site")
    with http.server.HTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving site/ at http://localhost:{port}")
        httpd.serve_forever()
