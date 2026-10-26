import json
import os
import time

RUNS = 0


def handler(event, context):
    global RUNS
    RUNS += 1
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report = {
        "ok": True,
        "service": "lmweblab-s06-scheduled-report",
        "run_id": os.environ.get("RUN_ID", "demo01"),
        "bucket": os.environ.get("BUCKET_NAME", "lmaws-tf-s06-demo01"),
        "table": os.environ.get("TABLE_NAME", "lmaws_tf_s06_runs_demo01"),
        "scheduled_runs": RUNS,
        "latest_iso": now_iso,
        "time_ns": time.time_ns(),
    }
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(report),
    }
