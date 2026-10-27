import html
import json
import os
import time

RUNS = 0
TABLE_NAME = os.environ.get("TABLE_NAME", "lmaws_s06_runs_demo")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "lmaws-s06-report-demo")
if os.environ.get("LMWEBLAB_OFFLINE") == "1":
    S3 = None
    DDB = None
else:
    import boto3
    S3 = boto3.client("s3")
    DDB = boto3.resource("dynamodb").Table(TABLE_NAME)


def _json_default(value):
    if hasattr(value, "as_tuple"):
        return int(value) if value == int(value) else float(value)
    return str(value)


def _response(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}, "body": json.dumps(body, default=_json_default)}


def _latest_report():
    if S3 is not None:
        try:
            body = S3.get_object(Bucket=BUCKET_NAME, Key="latest.json")["Body"].read()
            return json.loads(body)
        except Exception as error:
            code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
            if code not in ("NoSuchKey", "NoSuchBucket", "404"):
                raise
    if DDB is not None:
        item = DDB.get_item(Key={"pk": "latest"}).get("Item")
        if item:
            return item
    return None


def _scheduled_report():
    global RUNS
    if DDB is not None:
        counter = DDB.update_item(Key={"pk": "counter"}, UpdateExpression="ADD runs :one", ExpressionAttributeValues={":one": 1}, ReturnValues="UPDATED_NEW")
        RUNS = int(counter["Attributes"]["runs"])
    else:
        RUNS += 1
    report = {"ok": True, "service": "lmweblab-s06-scheduled-report", "run_id": os.environ.get("RUN_ID", "demo01"), "bucket": BUCKET_NAME, "table": TABLE_NAME, "scheduled_runs": RUNS, "latest_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "time_ns": time.time_ns()}
    if DDB is not None:
        DDB.put_item(Item={"pk": "latest", **report})
        DDB.put_item(Item={"pk": "report#" + str(RUNS), "run_seq": RUNS, **report})
    if S3 is not None:
        encoded = json.dumps(report, default=_json_default).encode("utf-8")
        S3.put_object(Bucket=BUCKET_NAME, Key="latest.json", Body=encoded, ContentType="application/json")
        S3.put_object(Bucket=BUCKET_NAME, Key="latest.html", Body=("<html><body><pre>" + html.escape(encoded.decode("utf-8")) + "</pre></body></html>").encode("utf-8"), ContentType="text/html")
    return _response(200, report)


def handler(event, context):
    if isinstance(event, dict) and event.get("source") == "aws.events":
        return _scheduled_report()
    report = _latest_report()
    if report is None:
        return _response(404, {"ok": False, "error": "report not ready"})
    return _response(200, report)
