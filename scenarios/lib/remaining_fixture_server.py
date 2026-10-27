#!/usr/bin/env python3
"""Loopback HTTP server for offline scenarios 08/09; boto3 is always fake."""
from __future__ import annotations
import importlib.util, json, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
scenario, ready, stop = sys.argv[1:4]
from remaining_fake_boto3 import Boto3
class SQS:
    def __init__(self): self.messages=[]; self.dlq=[]; self.attempts={}
    def send_message(self, **kw):
        mid="fixture-" + str(len(self.messages)+len(self.dlq)+1); self.messages.append({"MessageId":mid,"MessageBody":kw.get("MessageBody","")}); return {"MessageId": mid}
class Fake(Boto3):
    def __init__(self): super().__init__(); self.sqs=SQS()
    def client(self, service):
        if service == "sqs": return self.sqs
        return super().client(service)
fake = Fake(); sys.modules["boto3"] = fake
os.environ.setdefault("LMWEBLAB_DEMO_PASSWORD", "correct-horse")
os.environ.setdefault("RUN_ID", "fixture"); os.environ.setdefault("QUEUE_URL", "lmaws_queue"); os.environ.setdefault("TABLE_NAME", "lmaws_worker" if scenario == "07" else ("lmaws_session" if scenario == "08" else "lmaws_shortener"))
paths = {"08": root / "08-session-login-demo/lmaws/assets/session_login.py", "09": root / "09-url-shortener/lmaws/assets/url_shortener.py", "07": root / "07-sqs-worker/lmaws/assets/api.py"}
spec = importlib.util.spec_from_file_location("scenario_" + scenario, paths[scenario]); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
worker = None
if scenario == "07":
    ws = importlib.util.spec_from_file_location("worker", root / "07-sqs-worker/lmaws/assets/worker.py"); worker = importlib.util.module_from_spec(ws); ws.loader.exec_module(worker)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def _call(self, method, body=""):
        headers = {k.lower(): v for k, v in self.headers.items()}
        event = {"requestContext": {"http": {"method": method}}, "rawPath": urlparse(self.path).path, "headers": headers, "body": body, "cookies": [headers["cookie"]] if "cookie" in headers else []}
        try:
            if scenario == "07" and urlparse(self.path).path == "/worker":
                out = worker.handler(json.loads(body or "{}"), None)
                out = {"statusCode": 200, "headers": {"content-type": "application/json"}, "body": json.dumps(out)}
            else: out = mod.handler(event, None)
        except Exception as exc:
            out = {"statusCode": 500, "headers": {"content-type": "application/json"}, "body": '{"error":"fixture exception: ' + str(exc).replace('"', "'") + '"}'}
        data = out.get("body", "").encode(); self.send_response(out.get("statusCode", 500));
        for k, v in out.get("headers", {}).items(): self.send_header(k, str(v))
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def _drain(self):
        if scenario != "07": return
        q=fake.sqs
        while q.messages:
            msg=q.messages[0]; mid=msg["MessageId"]; count=q.attempts.get(mid,0)+1; q.attempts[mid]=count
            out=worker.handler({"Records":[{"messageId":mid,"body":msg["MessageBody"]}]},None)
            if out.get("batchItemFailures"):
                if count >= 3: q.dlq.append(q.messages.pop(0))
                else: break
            else: q.messages.pop(0)
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/__clock":
            from urllib.parse import parse_qs
            os.environ["LMWEBLAB_NOW"] = parse_qs(parsed.query).get("now", ["0"])[0]; self.send_response(204); self.end_headers(); return
        if scenario == "07":
            self._drain(); path=parsed.path
            if path.startswith("/tasks/"):
                key=path.rsplit("/",1)[-1]; row=fake.tables[os.environ["TABLE_NAME"]].rows.get(key); out={"statusCode":200,"headers":{"content-type":"application/json"},"body":json.dumps(row or {"status":"pending"})}; data=out["body"].encode(); self.send_response(200); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
            if path == "/dlq":
                out={"messages":[m["MessageBody"] for m in fake.sqs.dlq]}; data=json.dumps(out).encode(); self.send_response(200); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
        self._call("GET")
    def do_HEAD(self): self._call("HEAD")
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0")); self._call("POST", self.rfile.read(n).decode())

server = ThreadingHTTPServer(("127.0.0.1", int(os.getenv("LMWEBLAB_FIXTURE_PORT", "0"))), Handler); Path(ready).write_text(f"http://127.0.0.1:{server.server_port}\n")
t = threading.Thread(target=server.serve_forever, daemon=True); t.start(); deadline = time.time() + 300
try:
    while time.time() < deadline and not Path(stop).exists(): time.sleep(.05)
finally: server.shutdown(); server.server_close()
