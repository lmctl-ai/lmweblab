import html
import json
import os
import time
import urllib.request
import uuid

TABLE_NAME = os.environ.get("TABLE_NAME", "lmaws_tf_s04_table_demo01")
TTL_SECONDS = int(os.environ.get("TTL_SECONDS", "3600"))
MEM_ENTRIES = []
if os.environ.get("LMWEBLAB_OFFLINE") == "1":
    TABLE = None
else:
    try:
        import boto3
        TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
    except Exception:
        raise


def handler(event, context):
    method = ((event or {}).get("requestContext") or {}).get("http", {}).get("method", "GET")
    qs = (event or {}).get("queryStringParameters") or {}
    try:
        limit = max(1, min(50, int(qs.get("limit", "10"))))
        offset = max(0, int(qs.get("offset", "0")))
    except (TypeError, ValueError):
        return {"statusCode": 400, "body": json.dumps({"ok": False, "error": "invalid pagination"})}

    if method == "POST":
        raw_body = (event or {}).get("body") or "{}"
        try:
            payload = json.loads(raw_body)
        except (TypeError, ValueError):
            return {"statusCode": 400, "body": json.dumps({"ok": False, "error": "invalid JSON"})}
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
            "body": json.dumps({"ok": True, "table": TABLE_NAME, "entry": item}),
        }

    now_s = int(time.time())
    if TABLE is not None:
        all_items = TABLE.scan(Limit=min(50, offset + limit)).get("Items", [])
        page = [x for x in all_items if int(x.get("expires_at", 0)) > now_s][offset : offset + limit]
        total = len([x for x in all_items if int(x.get("expires_at", 0)) > now_s])
    else:
        now_s = int(time.time())
        live = [x for x in MEM_ENTRIES if int(x.get("expires_at", 0)) > now_s]
        page = live[offset : offset + limit]
        total = len(live)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(
            {
                "ok": True,
                "table": TABLE_NAME,
                "total": total,
                "offset": offset,
                "limit": limit,
                "items": page,
            }
        ),
    }
