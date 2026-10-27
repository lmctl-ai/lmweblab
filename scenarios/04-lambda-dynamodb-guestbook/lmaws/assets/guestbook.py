import html
import json
import os
import time
import urllib.request
import uuid
import base64

TABLE_NAME = os.environ.get("TABLE_NAME", "lmaws_tf_s04_table_demo01")
TTL_SECONDS = int(os.environ.get("TTL_SECONDS", "3600"))
MEM_ENTRIES = []
COLD_START = True


def _with_cold_header(response, cold):
    response = dict(response)
    headers = dict(response.get("headers") or {})
    headers["X-Lmweblab-Cold-Start"] = "true" if cold else "false"
    response["headers"] = headers
    return response

def json_default(value):
    return (int(value) if value==int(value) else float(value)) if hasattr(value,"as_tuple") else str(value)
if os.environ.get("LMWEBLAB_OFFLINE") == "1":
    TABLE = None
else:
    try:
        import boto3
        TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
    except Exception:
        raise


def _handler(event, context):
    method = ((event or {}).get("requestContext") or {}).get("http", {}).get("method", "GET")
    qs = (event or {}).get("queryStringParameters") or {}
    try:
        limit = max(1, min(50, int(qs.get("limit", "10"))))
        cursor = qs.get("cursor", "")
    except (TypeError, ValueError):
        return {"statusCode": 400, "body": json.dumps({"ok": False, "error": "invalid pagination"})}

    if method == "POST":
        raw_body = (event or {}).get("body") or "{}"
        if not isinstance(raw_body,str) or len(raw_body.encode("utf-8")) > 8192:
            return {"statusCode":413,"body":json.dumps({"ok":False,"error":"body too large"})}
        try:
            payload = json.loads(raw_body)
        except (TypeError, ValueError):
            return {"statusCode": 400, "body": json.dumps({"ok": False, "error": "invalid JSON"})}
        if not isinstance(payload,dict) or len(str(payload.get("author","")))>80 or len(str(payload.get("message","")))>1024:
            return {"statusCode":400,"body":json.dumps({"ok":False,"error":"bounded object fields required"})}
        author = html.escape(str(payload.get("author", "anonymous")), quote=True)
        message = html.escape(str(payload.get("message", "")), quote=True)
        now_s = int(time.time())
        item = {
            "id": str(uuid.uuid4()),
            "author": author,
            "message": message,
            "created_at": now_s,
            "expires_at": now_s + TTL_SECONDS,
        }
        item["pk"] = item["id"]
        if TABLE is not None:
            TABLE.put_item(Item=item)
        else:
            MEM_ENTRIES.append(item)
        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps({"ok": True, "table": TABLE_NAME, "entry": item}, default=json_default),
        }

    now_s = int(time.time())
    if TABLE is not None:
        start = None
        if cursor:
            try:
                if len(cursor)>2048: raise ValueError("cursor too large")
                start = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
                if not isinstance(start,dict) or set(start)!={"pk"} or not isinstance(start["pk"],str) or len(start["pk"])>1024: raise ValueError("invalid cursor key")
            except Exception:
                return {"statusCode": 400, "body": json.dumps({"ok": False, "error": "invalid cursor"})}
        response = TABLE.scan(Limit=limit, **({"ExclusiveStartKey": start} if start else {}))
        page = [x for x in response.get("Items", []) if int(x.get("expires_at", 0)) > now_s]
        next_key = response.get("LastEvaluatedKey")
        next_cursor = base64.urlsafe_b64encode(json.dumps(next_key).encode()).decode() if next_key else ""
        total = len(page)
    else:
        now_s = int(time.time())
        live = [x for x in MEM_ENTRIES if int(x.get("expires_at", 0)) > now_s]
        try:
            offset = int(cursor or "0") if cursor else 0
            if offset<0: raise ValueError("negative offset")
        except ValueError:
            return {"statusCode":400,"body":json.dumps({"ok":False,"error":"invalid cursor"})}
        page = live[offset : offset + limit]
        next_cursor = str(offset + limit) if offset + limit < len(live) else ""
        total = len(page)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(
            {
                "ok": True,
                "table": TABLE_NAME,
                "total": total,
                "limit": limit,
                "items": page,
                "next_cursor": next_cursor,
            }
        , default=json_default),
    }


def handler(event, context):
    global COLD_START
    cold = COLD_START
    COLD_START = False
    return _with_cold_header(_handler(event, context), cold)
