import json
import os
import time


def handler(event, context):
    path = (event or {}).get("rawPath", "/api/status")
    qs = (event or {}).get("queryStringParameters") or {}
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(
            {
                "ok": True,
                "service": "lmweblab-s05-static-plus-api",
                "run_id": os.environ.get("RUN_ID", "demo01"),
                "path": path,
                "query": qs,
                "timestamp": time.time(),
            }
        ),
    }
