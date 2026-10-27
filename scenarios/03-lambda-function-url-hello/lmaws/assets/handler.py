import json
import os
import time

COLD_START = True
INVOCATIONS = 0


def handler(event, context):
    global COLD_START, INVOCATIONS
    is_cold = COLD_START
    COLD_START = False
    INVOCATIONS += 1

    qs = (event or {}).get("queryStringParameters") or {}
    name = str(qs.get("name", "world"))
    path = (event or {}).get("rawPath", "/")

    body = {
        "ok": True,
        "service": "lmweblab-s03-lambda-hello",
        "run_id": os.environ.get("RUN_ID", "demo01"),
        "path": path,
        "greeting": f"Hello, {name}!",
        "cold_start": is_cold,
        "invocation": INVOCATIONS,
        "timestamp": time.time(),
        "time_ns": time.time_ns(),
    }
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body),
    }
