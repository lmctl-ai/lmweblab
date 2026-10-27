"""Deterministic URL-shortener fixture; production uses DynamoDB conditional put/update."""
import json, os, re
from decimal import Decimal
from urllib.parse import urlparse
import boto3

def _table(): return boto3.resource("dynamodb").Table(os.getenv("TABLE_NAME", os.getenv("LMWEBLAB_SHORTENER_TABLE", "lmaws_shortener")))

_links = {"demo": {"target": "https://example.com/welcome", "hits": 0, "status": 302}, "perm": {"target": "https://example.com/docs", "hits": 0, "status": 301}}

def _reply(status, body, headers=None):
    return {"statusCode": status, "headers": {"content-type": "application/json", **(headers or {})}, "body": json.dumps(body, sort_keys=True, default=lambda v: int(v) if isinstance(v, Decimal) and v == int(v) else str(v))}

def handler(event, context=None):
    path = event.get("rawPath", event.get("path", "/")); method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", "GET"))
    code = path.rsplit("/", 1)[-1]
    if path == "/links" and method == "POST":
        try: body = json.loads(event.get("body") or "{}")
        except (TypeError, ValueError): return _reply(400, {"error": "invalid json"})
        if not isinstance(body,dict): return _reply(400,{"error":"invalid request"})
        code, target = str(body.get("code", "")), str(body.get("target", ""))
        if not re.fullmatch(r"[a-z0-9_-]{2,32}", code) or not target.startswith("https://") or len(target) > 2048 or not urlparse(target).hostname or any(c.isspace() or ord(c)<32 for c in target):
            return _reply(400, {"error": "code or target rejected"})
        if _table().get_item(Key={"pk": code},ConsistentRead=True).get("Item") or code in _links: return _reply(409, {"error": "code exists"})
        try: status = int(body.get("status", 302))
        except (ValueError, TypeError): return _reply(400, {"error": "status rejected"})
        if status not in (301, 302): return _reply(400, {"error": "status rejected"})
        try: _table().put_item(Item={"pk": code, "target": target, "hits": 0, "status": status, "run_id": os.getenv("RUN_ID", "fixture")}, ConditionExpression="attribute_not_exists(pk)")
        except Exception as exc:
            if getattr(exc,"response",{}).get("Error",{}).get("Code")=="ConditionalCheckFailedException" or exc.__class__.__name__=="ConditionalCheckFailedException": return _reply(409,{"error":"code exists"})
            raise
        return _reply(201, {"code": code, "target": target})
    if path in ("/", ""):
        return _reply(200, {"service": "url-shortener", "routes": ["/demo", "/perm"]})
    row = _table().get_item(Key={"pk": code},ConsistentRead=True).get("Item")
    if not row:
        row = _links.get(code)
        if row:
            row = {"pk": code, **row}
            try: _table().put_item(Item=row,ConditionExpression="attribute_not_exists(pk)")
            except Exception as exc:
                if getattr(exc,"response",{}).get("Error",{}).get("Code")!="ConditionalCheckFailedException" and exc.__class__.__name__!="ConditionalCheckFailedException": raise
                row = _table().get_item(Key={"pk":code},ConsistentRead=True).get("Item")
    if not row: return _reply(404, {"error": "unknown code"})
    if method not in ("GET", "HEAD"): return _reply(405, {"error": "method not allowed"})
    updated = _table().update_item(Key={"pk": code}, UpdateExpression="SET hits = if_not_exists(hits, :zero) + :one", ExpressionAttributeValues={":zero": 0, ":one": 1}, ReturnValues="ALL_NEW",ConditionExpression="attribute_exists(pk)")
    row = {**row, **updated.get("Attributes", {})}
    return _reply(row["status"], {"code": code, "hits": row["hits"]}, {"location": row["target"], "cache-control": "no-store"})
