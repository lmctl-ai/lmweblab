#!/usr/bin/env python3
"""Loopback HTTP adapter for the offline Lambda scenario handlers."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


scenario = sys.argv[1]
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
os.environ.setdefault("LMWEBLAB_OFFLINE", "1")
ready = Path(sys.argv[2])
stop = Path(sys.argv[3])
paths = {
    "03": ROOT / "03-lambda-function-url-hello/lmcloud/assets/handler.py",
    "04": ROOT / "04-lambda-dynamodb-guestbook/lmaws/assets/guestbook.py",
    "05": ROOT / "05-static-plus-api/lmaws/assets/api.py",
    "06": ROOT / "06-scheduled-report/lmaws/assets/reporter.py",
}
module = load(paths[scenario], "s" + scenario)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _send(self, status: int, body: str, content_type: str = "application/json", extra: dict[str, str] | None = None):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if scenario == "05" and parsed.path == "/":
            self._send(200, "<html><body><h1>lmweblab static fixture</h1></body></html>", "text/html; charset=utf-8")
            return
        if scenario == "05":
            event = {"rawPath": parsed.path, "queryStringParameters": {k: v[-1] for k, v in parse_qs(parsed.query).items()}}
        elif scenario == "04":
            event = {"requestContext": {"http": {"method": "GET"}}, "queryStringParameters": {k: v[-1] for k, v in parse_qs(parsed.query).items()}}
        else:
            event = {}
        result = module.handler(event, None)
        self._send(result["statusCode"], result["body"], extra=result.get("headers"))

    def do_POST(self):  # noqa: N802
        size = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(size).decode("utf-8")
        event = {"requestContext": {"http": {"method": "POST"}}, "body": body}
        result = module.handler(event, None)
        self._send(result["statusCode"], result["body"])


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
ready.write_text(f"http://127.0.0.1:{server.server_port}\n", encoding="utf-8")
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
deadline = time.time() + 300
try:
    while time.time() < deadline and not stop.exists():
        time.sleep(0.05)
finally:
    server.shutdown()
    server.server_close()
