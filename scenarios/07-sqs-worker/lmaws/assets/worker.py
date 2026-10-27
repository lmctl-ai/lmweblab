import json, os
import boto3

def handler(event, context=None):
    failures=[]; processed=0
    table=boto3.resource("dynamodb").Table(os.getenv("TABLE_NAME",os.getenv("LMWEBLAB_WORK_TABLE","lmaws_worker")))
    for record in event.get("Records", []):
        mid=str(record.get("messageId", record.get("message_id", ""))); body=record.get("body", "")
        try: payload=json.loads(body)
        except (TypeError, ValueError): payload={}
        if payload.get("task") == "poison": failures.append({"itemIdentifier":mid}); continue
        if not mid: continue
        if table.get_item(Key={"pk":mid}).get("Item"): continue
        try:
            table.put_item(Item={"pk":mid,"task":str(payload.get("task", "")),"run_id":os.getenv("RUN_ID",os.getenv("LMWEBLAB_RUN_ID","fixture")),"status":"processed"}, ConditionExpression="attribute_not_exists(pk)")
        except Exception as exc:
            code=getattr(exc, "response", {}).get("Error", {}).get("Code", "") if hasattr(exc, "response") else exc.__class__.__name__
            if code not in ("ConditionalCheckFailedException", "ConditionalCheckFailed"): raise
            continue
        processed += 1
    return {"batchItemFailures":failures,"processed":processed}
