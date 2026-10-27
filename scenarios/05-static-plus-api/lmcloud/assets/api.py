import json
import os
import time

COLD_START = True


def handler(event, context):
    global COLD_START
    is_cold = COLD_START
    COLD_START = False

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
                "cold_start": is_cold,
                "path": path,
                "query": qs,
                "timestamp": time.time(),
                "time_ns": time.time_ns(),
            }
        ),
    }
