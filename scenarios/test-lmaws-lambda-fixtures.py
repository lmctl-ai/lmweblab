#!/usr/bin/env python3
"""Exercise the committed Lambda handlers without AWS credentials."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    rows: list[dict] = []

    class FakeTable:
        def put_item(self, *, Item): rows.append(Item)
        def update_item(self, **kwargs):
            self.counter=getattr(self,"counter",0)+1
            return {"Attributes":{"runs":self.counter}}
        def scan(self, *, Limit, **kwargs):
            start = kwargs.get("ExclusiveStartKey", {}).get("pk", "")
            index = next((i + 1 for i, row in enumerate(rows) if row.get("pk") == start), 0)
            page = rows[index : index + Limit]
            out = {"Items": page}
            if index + Limit < len(rows): out["LastEvaluatedKey"] = {"pk": page[-1]["pk"]}
            return out
        def get_item(self, *, Key):
            item = next((row for row in rows if row.get("pk") == Key.get("pk")), None)
            return {"Item": item} if item else {}

    tables={}
    class FakeDynamo:
        def Table(self, name): return tables.setdefault(name,FakeTable())

    class FakeS3Client:
        def __init__(self): self.objects = {}
        def put_object(self, **kwargs): self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs
        def get_object(self, **kwargs):
            key = (kwargs["Bucket"], kwargs["Key"])
            if key not in self.objects:
                error = RuntimeError("NoSuchKey")
                error.response = {"Error": {"Code": "NoSuchKey"}}
                raise error
            return {"Body": types.SimpleNamespace(read=lambda: self.objects[key]["Body"])}

    dynamo = FakeDynamo()
    s3 = FakeS3Client()
    fake_boto3 = types.SimpleNamespace(resource=lambda _name: dynamo, client=lambda _name: s3)
    sys.modules["boto3"] = fake_boto3
    os.environ["TABLE_NAME"] = "lmaws_s04_fixture"
    guest = load(ROOT / "04-lambda-dynamodb-guestbook/lmaws/assets/guestbook.py", "guestbook")
    first = guest.handler({"requestContext": {"http": {"method": "POST"}}, "body": json.dumps({"author": "A <b>", "message": "<script>alert(1)</script>"})}, None)
    assert first["statusCode"] == 201
    body = json.loads(first["body"])
    assert "&lt;script&gt;" in body["entry"]["message"]
    guest.handler({"requestContext": {"http": {"method": "POST"}}, "body": json.dumps({"author": "B", "message": "second"})}, None)
    page = guest.handler({"requestContext": {"http": {"method": "GET"}}, "queryStringParameters": {"limit": "1", "offset": "0"}}, None)
    page_body = json.loads(page["body"])
    assert page["statusCode"] == 200 and page_body["total"] == 1 and page_body["next_cursor"]
    second_page = guest.handler({"requestContext": {"http": {"method": "GET"}}, "queryStringParameters": {"limit": "1", "cursor": page_body["next_cursor"]}}, None)
    assert json.loads(second_page["body"])["items"][0]["message"] == "second"
    # DynamoDB returns Decimal values and can retain expired items until its
    # background TTL sweep. The handler filters these rows before serializing.
    rows.append({"pk": "expired", "id": "expired", "message": "old", "expires_at": Decimal("1")})
    live_page = json.loads(guest.handler({"requestContext": {"http": {"method": "GET"}}, "queryStringParameters": {"limit": "10"}}, None)["body"])
    assert all(item["id"] != "expired" for item in live_page["items"])

    api = load(ROOT / "05-static-plus-api/lmaws/assets/api.py", "api")
    response = api.handler({"rawPath": "/api/info", "queryStringParameters": {"q": "fixture"}}, None)
    assert response["statusCode"] == 200 and json.loads(response["body"])["path"] == "/api/info"

    os.environ["TABLE_NAME"] = "lmaws_s06_fixture"
    os.environ["BUCKET_NAME"] = "lmaws-s06-fixture"
    reporter = load(ROOT / "06-scheduled-report/lmaws/assets/reporter.py", "reporter")
    before = reporter.handler({}, None)
    assert before["statusCode"] == 404
    one = json.loads(reporter.handler({"source": "aws.events", "detail-type": "Scheduled Event"}, None)["body"])
    two = json.loads(reporter.handler({"source": "aws.events", "detail-type": "Scheduled Event"}, None)["body"])
    assert one["scheduled_runs"] == 1 and two["scheduled_runs"] == 2
    writes_before_poll = len(s3.objects)
    polled = json.loads(reporter.handler({}, None)["body"])
    polled_again = json.loads(reporter.handler({}, None)["body"])
    assert polled["scheduled_runs"] == 2 and polled_again["scheduled_runs"] == 2
    assert len(s3.objects) == writes_before_poll and len([row for row in rows if row.get("pk", "").startswith("report#")]) == 2
    cold=load(ROOT / "06-scheduled-report/lmaws/assets/reporter.py","reporter_cold")
    assert json.loads(cold.handler({},None)["body"])["scheduled_runs"]==2,"HTTP poll changed schedule state"
    assert s3.objects[("lmaws-s06-fixture", "latest.html")]["ContentType"] == "text/html"
    assert guest.handler({"requestContext":{"http":{"method":"POST"}},"body":"[]"},None)["statusCode"]==400
    assert guest.handler({"requestContext":{"http":{"method":"POST"}},"body":json.dumps({"message":"x"*9000})},None)["statusCode"]==413
    print("PASS Lambda fixtures: escaping, pagination, API routing, and scheduled persistence")


if __name__ == "__main__":
    main()
