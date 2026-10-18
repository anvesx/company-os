"""Local web server for the console: static files plus the JSON API. Run: python3 -m web_console.serve [--port 8800] [--reset]."""
import argparse
import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .console_api import Console, route

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
DEFAULT_STATE = os.path.join(HERE, "state")
MAX_BODY = 1_000_000


def make_handler(console):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, status, data, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, status, obj):
            self._send(status, json.dumps(obj).encode(), "application/json; charset=utf-8")

        def _static(self, path):
            name = "index.html" if path in ("", "/") else path.lstrip("/")
            full = os.path.realpath(os.path.join(STATIC, name))
            if not full.startswith(STATIC + os.sep) or not os.path.isfile(full):
                return self._json(404, {"ok": False, "error": "Page not found."})
            kind = mimetypes.guess_type(full)[0] or "application/octet-stream"
            with open(full, "rb") as f:
                self._send(200, f.read(), kind + ("; charset=utf-8" if kind.startswith("text/") or "javascript" in kind else ""))

        def do_GET(self):
            url = urlparse(self.path)
            if url.path.startswith("/api/"):
                status, obj = route(console, "GET", url.path, parse_qs(url.query), None)
                return self._json(status, obj)
            self._static(url.path)

        def do_POST(self):
            url = urlparse(self.path)
            length = min(int(self.headers.get("Content-Length") or 0), MAX_BODY)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                return self._json(400, {"ok": False, "error": "The request was not valid JSON."})
            status, obj = route(console, "POST", url.path, parse_qs(url.query), body)
            self._json(status, obj)

    return Handler


def make_server(console, port=8800):
    return HTTPServer(("127.0.0.1", port), make_handler(console))


def serve_in_thread(state_dir, port=0):
    """For tests. The console is built inside the server thread, because SQLite connections stay in their thread."""
    ready, box = threading.Event(), {}

    def target():
        try:
            box["console"] = Console(state_dir)
            box["server"] = make_server(box["console"], port)
        except Exception as e:
            box["error"] = e
            ready.set()
            return
        ready.set()
        box["server"].serve_forever()
        box["console"].close()

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    ready.wait(30)
    if "error" in box:
        raise box["error"]
    return box["server"], thread


def main(argv=None):
    parser = argparse.ArgumentParser(description="Company OS web console")
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--reset", action="store_true", help="start from an empty state")
    parser.add_argument("--state-dir", default=DEFAULT_STATE)
    args = parser.parse_args(argv)
    console = Console(args.state_dir, reset=args.reset)
    server = make_server(console, args.port)
    print(f"Company OS console: http://localhost:{args.port}  (simulated date {console.cos.clock.now}). Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        console.close()


if __name__ == "__main__":
    main()
