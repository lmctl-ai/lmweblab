import html
import json
import os
import time
import uuid
from decimal import Decimal

try:
    import boto3
except ImportError:
    boto3 = None

TABLE_NAME = os.environ.get("TABLE_NAME", "lmaws_tf_s04_entries_demo01")
TTL_SECONDS = int(os.environ.get("TTL_SECONDS", "3600"))
COLD_START = True
MEM_ENTRIES = []


def _to_native(obj):
    if isinstance(obj, list):
        return [_to_native(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def handler(event, context):
    global COLD_START
    is_cold = COLD_START
    COLD_START = False

    method = ((event or {}).get("requestContext") or {}).get("http", {}).get("method", "GET")
    qs = (event or {}).get("queryStringParameters") or {}
    limit = max(1, min(50, int(qs.get("limit", "10"))))
    offset = max(0, int(qs.get("offset", "0")))

    table = None
    if boto3 is not None and os.environ.get("AWS_EXECUTION_ENV"):
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(TABLE_NAME)

    if method == "POST":
        raw_body = (event or {}).get("body") or "{}"
        payload = json.loads(raw_body)
        author = html.escape(str(payload.get("author", "anonymous")), quote=True)
        message = html.escape(str(payload.get("message", "")), quote=True)
        now_ms = int(time.time() * 1000)
        now_s = int(time.time())
        item = {
            "id": f"{now_ms}-{uuid.uuid4().hex[:8]}",
            "author": author,
            "message": message,
            "created_at": now_ms,
            "expires_at": now_s + TTL_SECONDS,
        }
        if table is not None:
            table.put_item(Item=item)
        else:
            MEM_ENTRIES.append(item)
        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json; charset=utf-8",
                "Cache-Control": "no-store",
            },
            "body": json.dumps(
                {
                    "ok": True,
                    "cold_start": is_cold,
                    "table": TABLE_NAME,
                    "ttl_attribute": "expires_at",
                    "entry": item,
                }
            ),
        }

    if table is not None:
        resp = table.scan()
        items = _to_native(resp.get("Items", []))
        items.sort(key=lambda x: x.get("created_at", 0))
    else:
        items = list(MEM_ENTRIES)

    page = items[offset : offset + limit]
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(
            {
                "ok": True,
                "cold_start": is_cold,
                "table": TABLE_NAME,
                "ttl_attribute": "expires_at",
                "total": len(items),
                "offset": offset,
                "limit": limit,
                "items": page,
            }
        ),
    }
