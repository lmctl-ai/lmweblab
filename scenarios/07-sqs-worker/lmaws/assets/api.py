import json, os, uuid
import boto3

def handler(event, context=None):
    path=event.get("rawPath", event.get("path", "/")); method=event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", "GET"))
    if method == "GET" and path.startswith("/tasks/"):
        key=path.rsplit("/",1)[-1]; row=boto3.resource("dynamodb").Table(os.getenv("TABLE_NAME","lmaws_worker")).get_item(Key={"pk":key}).get("Item")
        return {"statusCode":200,"headers":{"content-type":"application/json"},"body":json.dumps(row or {"status":"pending"})}
    if method == "GET" and path == "/dlq":
        out=boto3.client("sqs").receive_message(QueueUrl=os.getenv("DLQ_URL","lmaws_worker_dlq"),MaxNumberOfMessages=1,VisibilityTimeout=0)
        return {"statusCode":200,"headers":{"content-type":"application/json"},"body":json.dumps({"messages":[m.get("Body","") for m in out.get("Messages",[])]})}
    if method != "POST": return {"statusCode":200,"headers":{"content-type":"application/json"},"body":json.dumps({"service":"sqs-worker"})}
    try: body=json.loads(event.get("body") or "{}")
    except (TypeError, ValueError): return {"statusCode":400,"headers":{"content-type":"application/json"},"body":json.dumps({"error":"invalid json"})}
    if not isinstance(body,dict): return {"statusCode":400,"body":"{}"}
    task=str(body.get("task", ""));
    if not task or len(task)>256: return {"statusCode":400,"headers":{"content-type":"application/json"},"body":json.dumps({"error":"task required"})}
    msg=json.dumps({"task":task,"run_id":os.getenv("RUN_ID",os.getenv("LMWEBLAB_RUN_ID","fixture")),"message_id":uuid.uuid4().hex})
    out=boto3.client("sqs").send_message(QueueUrl=os.getenv("QUEUE_URL",os.getenv("LMWEBLAB_QUEUE_URL","lmaws_queue")),MessageBody=msg)
    return {"statusCode":202,"headers":{"content-type":"application/json"},"body":json.dumps({"accepted":True,"message_id":out.get("MessageId", "fixture")})}
