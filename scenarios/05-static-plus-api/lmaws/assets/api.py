import json
import os
import time
COLD_START = True


def _handler(event, context):
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


def handler(event, context):
    global COLD_START
    cold = COLD_START
    COLD_START = False
    response = dict(_handler(event, context))
    headers = dict(response.get("headers") or {})
    headers["X-Lmweblab-Cold-Start"] = "true" if cold else "false"
    response["headers"] = headers
    return response
