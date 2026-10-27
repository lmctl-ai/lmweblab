import html
import json
import os
import time

RUNS = 0
if os.environ.get("LMWEBLAB_OFFLINE") == "1":
    S3 = None
    DDB = None
else:
    import boto3
    S3 = boto3.client("s3")
    DDB = boto3.resource("dynamodb").Table(os.environ.get("TABLE_NAME", "lmaws_s06_runs_demo"))


def handler(event, context):
    global RUNS
    if DDB is not None:
        counter = DDB.update_item(Key={"pk":"counter"}, UpdateExpression="ADD runs :one", ExpressionAttributeValues={":one":1}, ReturnValues="UPDATED_NEW")
        RUNS = int(counter["Attributes"]["runs"])
    else:
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
    if DDB is not None:
        DDB.put_item(Item={"pk": "report#" + str(RUNS), "run_seq": RUNS, **report})
    if S3 is not None:
        S3.put_object(Bucket=report["bucket"], Key="latest.json", Body=json.dumps(report).encode("utf-8"), ContentType="application/json")
        S3.put_object(Bucket=report["bucket"], Key="latest.html", Body=("<html><body><pre>" + html.escape(json.dumps(report)) + "</pre></body></html>").encode("utf-8"), ContentType="text/html")
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(report),
    }
