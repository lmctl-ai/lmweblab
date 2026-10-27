"""Deterministic fixture for the session-login scenario; DynamoDB is the live backing store."""
import hmac, json, os, time, secrets
from decimal import Decimal
try:
    import boto3
except ImportError:
    boto3 = None
def _now():
    try: return int(float(os.getenv("LMWEBLAB_NOW", str(time.time()))))
    except ValueError: return int(time.time())

def _table():
    return boto3.resource("dynamodb").Table(os.getenv("TABLE_NAME", os.getenv("LMWEBLAB_SESSION_TABLE", "lmaws_session")))

def _reply(status, body, headers=None):
    return {"statusCode": status, "headers": {"content-type": "application/json", **(headers or {})}, "body": json.dumps(body, sort_keys=True, default=lambda v: int(v) if isinstance(v, Decimal) and v == int(v) else str(v))}

def handler(event, context=None):
    method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", "GET"))
    path = event.get("rawPath", event.get("path", "/"))
    try: body = json.loads(event.get("body") or "{}")
    except (TypeError, ValueError): return _reply(400, {"error": "invalid json"})
    if not isinstance(body,dict): return _reply(400,{"error":"invalid request"})
    cookies = event.get("cookies") or []
    if not cookies and event.get("headers"): cookies = [event["headers"].get("cookie", "")]
    sid_values = [part.strip().split("=", 1)[1] for chunk in cookies for part in chunk.split(";") if part.strip().startswith("sid=")]
    sid = sid_values[0] if sid_values and all(value == sid_values[0] for value in sid_values) else None
    now = _now()
    if path == "/login" and method == "POST":
        configured = os.getenv("LMWEBLAB_DEMO_PASSWORD", "")
        supplied = body.get("password")
        if str(body.get("user", "")) != "demo" or not configured or not isinstance(supplied, str) or not hmac.compare_digest(configured, supplied): return _reply(401, {"error": "invalid credentials"})
        sid = "s_" + secrets.token_hex(32); expires = now + int(os.getenv("TTL_SECONDS", os.getenv("LMWEBLAB_SESSION_TTL", "900")))
        _table().put_item(Item={"pk": sid, "user": body["user"], "expires_at": expires, "run_id": os.getenv("LMWEBLAB_RUN_ID", "fixture")})
        return _reply(200, {"ok": True, "user": body["user"], "expires_at": expires}, {"set-cookie": "sid=" + sid + "; HttpOnly; Secure; Path=/; SameSite=Lax"})
    if path == "/logout" and method == "POST":
        if sid: _table().delete_item(Key={"pk": sid})
        return _reply(200, {"ok": True}, {"set-cookie": "sid=; Max-Age=0; HttpOnly; Secure; Path=/; SameSite=Lax"})
    if path == "/me" and method == "GET":
        row = _table().get_item(Key={"pk": sid}, ConsistentRead=True).get("Item") if sid else None
        if not row or int(row["expires_at"]) <= now:
            if sid: _table().delete_item(Key={"pk": sid})
            return _reply(401, {"error": "unauthorized"})
        return _reply(200, {"user": row["user"], "expires_at": row["expires_at"]})
    if path == "/" and method == "GET":
        return {"statusCode":200,"headers":{"content-type":"text/html; charset=utf-8","cache-control":"no-store"},"body":FORM}
    return _reply(404,{"error":"not found"})

FORM = '<!doctype html><meta charset="utf-8"><title>Session login demo</title><h1>Ephemeral session login demo</h1><p>Demonstration only. No real user credentials.</p><form id="login"><input name="user" value="demo" autocomplete="off"><input name="password" type="password" autocomplete="off"><button>Login</button></form><button id="logout">Logout</button><pre id="result"></pre><script>login.onsubmit=async e=>{e.preventDefault();result.textContent=await(await fetch(\'/login\',{method:\'POST\',body:JSON.stringify(Object.fromEntries(new FormData(login)))})).text()};logout.onclick=async()=>{result.textContent=await(await fetch(\'/logout\',{method:\'POST\',body:\'{}\'})).text()}</script>'
