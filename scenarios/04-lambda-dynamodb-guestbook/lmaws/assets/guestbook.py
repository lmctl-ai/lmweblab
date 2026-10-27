import html
import json
import os
import time
import urllib.request
import uuid

TABLE_NAME = os.environ.get("TABLE_NAME", "lmaws_tf_s04_table_demo01")
TTL_SECONDS = int(os.environ.get("TTL_SECONDS", "3600"))
MEM_ENTRIES = []


def handler(event, context):
    method = ((event or {}).get("requestContext") or {}).get("http", {}).get("method", "GET")
    qs = (event or {}).get("queryStringParameters") or {}
    limit = max(1, min(50, int(qs.get("limit", "10"))))
    offset = max(0, int(qs.get("offset", "0")))

    if method == "POST":
        raw_body = (event or {}).get("body") or "{}"
        payload = json.loads(raw_body)
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
        MEM_ENTRIES.append(item)
        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps({"ok": True, "table": TABLE_NAME, "entry": item}),
        }

    page = MEM_ENTRIES[offset : offset + limit]
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(
            {
                "ok": True,
                "table": TABLE_NAME,
                "total": len(MEM_ENTRIES),
                "offset": offset,
                "limit": limit,
                "items": page,
            }
        ),
    }
