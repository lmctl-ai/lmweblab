#!/bin/bash
set -euxo pipefail

RUN_ID="__RUN_ID__"

cat >/usr/local/bin/lmweblab_server.py <<'PYEOF'
#!/usr/bin/env python3
import datetime
import html
import http.server
import json
import os
import socket
import threading
import time
import urllib.parse

RUN_ID = os.environ.get("LMWEBLAB_RUN_ID", "__RUN_ID__")
HOSTNAME = socket.gethostname()
COUNTER_LOCK = threading.Lock()
REQUEST_COUNTER = 0


def next_count():
    global REQUEST_COUNTER
    with COUNTER_LOCK:
        REQUEST_COUNTER += 1
        return REQUEST_COUNTER


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        raw_echo = ""
        for key in ("echo", "q", "msg", "input"):
            if key in params and len(params[key]) > 0:
                raw_echo = params[key][0]
                break
        if not raw_echo and parsed.query:
            raw_echo = parsed.query
        escaped_echo = html.escape(raw_echo, quote=True)

        now_ts = time.time()
        now_ns = time.time_ns()
        now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if parsed.path == "/healthz":
            payload = json.dumps({"ok": True, "run_id": RUN_ID, "hostname": HOSTNAME}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        count = next_count()

        if parsed.path == "/api/info":
            body_obj = {
                "status": "ok",
                "service": "lmweblab-app",
                "run_id": RUN_ID,
                "hostname": HOSTNAME,
                "counter": count,
                "timestamp": now_ts,
                "time_ns": now_ns,
                "time_iso": now_iso,
                "echo": escaped_echo,
            }
            payload = json.dumps(body_obj).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if parsed.path in ("/", "/index.html"):
            page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>lmweblab Dynamic App ({html.escape(RUN_ID, quote=True)})</title>
</head>
<body>
  <h1 id="app-title">lmweblab Dynamic App</h1>
  <p id="run-id">run_id: <span id="run-id-val">{html.escape(RUN_ID, quote=True)}</span></p>
  <p id="hostname">hostname: <span id="hostname-val">{html.escape(HOSTNAME, quote=True)}</span></p>
  <p id="counter">counter: <span id="counter-val">{count}</span></p>
  <p id="time">time: <span id="time-val">{now_iso} ({now_ns})</span></p>
  <p id="echo">echo: <span id="echo-val">{escaped_echo}</span></p>
</body>
</html>
"""
            payload = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        not_found = b'{"error":"not_found"}'
        self.send_response(404)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(not_found)))
        self.end_headers()
        self.wfile.write(not_found)


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 80), Handler)
    server.serve_forever()
PYEOF

sed -i "s/__RUN_ID__/${RUN_ID}/g" /usr/local/bin/lmweblab_server.py
chmod 0755 /usr/local/bin/lmweblab_server.py

cat >/etc/systemd/system/lmweblab-app.service <<EOF
[Unit]
Description=lmweblab dynamic Python HTTP server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment=LMWEBLAB_RUN_ID=${RUN_ID}
ExecStart=/usr/bin/python3 /usr/local/bin/lmweblab_server.py
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now lmweblab-app.service
