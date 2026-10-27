import json
import os
import time
from decimal import Decimal

try:
    import boto3
except ImportError:
    boto3 = None

BUCKET_NAME = os.environ.get("BUCKET_NAME", "lmaws-tf-s06-demo01")
TABLE_NAME = os.environ.get("TABLE_NAME", "lmaws_tf_s06_runs_demo01")
RUN_ID = os.environ.get("RUN_ID", "demo01")
COLD_START = True
MEM_RUNS = []


def _to_native(obj):
    if isinstance(obj, list):
        return [_to_native(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def _record_run(trigger_source):
    now_ms = int(time.time() * 1000)
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    s3_key = f"reports/run-{now_ms}.json"
    html_key = "reports/latest.html"
    report_doc = {
        "run_seq": now_ms,
        "run_id": RUN_ID,
        "trigger": trigger_source,
        "s3_key": s3_key,
        "html_key": html_key,
        "created_at_iso": now_iso,
    }
    html_doc = (
        "<!doctype html><html><head><meta charset='utf-8'><title>lmweblab Scheduled Report</title></head>"
        f"<body><h1>lmweblab Scheduled Report ({RUN_ID})</h1>"
        f"<p>Latest run_seq: {now_ms}</p><p>Trigger: {trigger_source}</p>"
        f"<p>Timestamp: {now_iso}</p></body></html>"
    )
    if boto3 is not None and os.environ.get("AWS_EXECUTION_ENV"):
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(report_doc).encode("utf-8"),
            ContentType="application/json",
        )
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key="reports/latest.json",
            Body=json.dumps(report_doc).encode("utf-8"),
            ContentType="application/json",
        )
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=html_key,
            Body=html_doc.encode("utf-8"),
            ContentType="text/html; charset=utf-8",
        )
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(TABLE_NAME)
        table.put_item(Item=report_doc)
    else:
        MEM_RUNS.append(report_doc)
    return report_doc


def handler(event, context):
    global COLD_START
    is_cold = COLD_START
    COLD_START = False

    ev = event or {}
    # EventBridge scheduled invocation
    if ev.get("source") == "aws.events" or ev.get("detail-type") == "Scheduled Event":
        rec = _record_run("aws.events")
        return {"ok": True, "recorded": rec}

    method = (ev.get("requestContext") or {}).get("http", {}).get("method", "GET")
    qs = ev.get("queryStringParameters") or {}
    path = ev.get("rawPath", "/")

    if method == "POST":
        rec = _record_run("manual")
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json; charset=utf-8",
                "Cache-Control": "no-store",
            },
            "body": json.dumps(
                {
                    "ok": True,
                    "service": "lmweblab-s06-scheduled-report",
                    "cold_start": is_cold,
                    "run_id": RUN_ID,
                    "recorded": rec,
                }
            ),
        }

    if path == "/html" or qs.get("format") == "html":
        html_body = f"<html><body><h1>lmweblab Scheduled Report ({RUN_ID})</h1></body></html>"
        if boto3 is not None and os.environ.get("AWS_EXECUTION_ENV"):
            try:
                s3 = boto3.client("s3")
                obj = s3.get_object(Bucket=BUCKET_NAME, Key="reports/latest.html")
                html_body = obj["Body"].read().decode("utf-8")
            except Exception:
                pass
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html; charset=utf-8",
                "Cache-Control": "no-store",
            },
            "body": html_body,
        }

    runs = []
    if boto3 is not None and os.environ.get("AWS_EXECUTION_ENV"):
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(TABLE_NAME)
        resp = table.scan()
        runs = _to_native(resp.get("Items", []))
        runs.sort(key=lambda x: x.get("run_seq", 0))
    else:
        runs = list(MEM_RUNS)

    eb_runs = [r for r in runs if r.get("trigger") == "aws.events"]
    latest = runs[-1] if runs else None
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(
            {
                "ok": True,
                "service": "lmweblab-s06-scheduled-report",
                "cold_start": is_cold,
                "run_id": RUN_ID,
                "bucket": BUCKET_NAME,
                "table": TABLE_NAME,
                "scheduled_runs": len(runs),
                "eventbridge_runs": len(eb_runs),
                "latest": latest,
                "runs": runs,
            }
        ),
    }
