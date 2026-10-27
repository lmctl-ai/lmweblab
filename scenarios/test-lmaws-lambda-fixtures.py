#!/usr/bin/env python3
"""Exercise the committed Lambda handlers without AWS credentials."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
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

    tables={}
    class FakeDynamo:
        def Table(self, name): return tables.setdefault(name,FakeTable())

    class FakeS3Client:
        def put_object(self, **kwargs): self.last = kwargs

    fake_boto3 = types.SimpleNamespace(resource=lambda _name: FakeDynamo(), client=lambda _name: FakeS3Client())
    sys.modules["boto3"] = fake_boto3
    guest = load(ROOT / "04-lambda-dynamodb-guestbook/lmaws/assets/guestbook.py", "guestbook")
    os.environ["TABLE_NAME"] = "lmaws_s04_fixture"
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

    api = load(ROOT / "05-static-plus-api/lmaws/assets/api.py", "api")
    response = api.handler({"rawPath": "/api/info", "queryStringParameters": {"q": "fixture"}}, None)
    assert response["statusCode"] == 200 and json.loads(response["body"])["path"] == "/api/info"

    reporter = load(ROOT / "06-scheduled-report/lmaws/assets/reporter.py", "reporter")
    one = json.loads(reporter.handler({}, None)["body"])
    two = json.loads(reporter.handler({}, None)["body"])
    assert one["scheduled_runs"] == 1 and two["scheduled_runs"] == 2
    cold=load(ROOT / "06-scheduled-report/lmaws/assets/reporter.py","reporter_cold")
    assert json.loads(cold.handler({},None)["body"])["scheduled_runs"]==3,"schedule counter lost on cold start"
    assert any(row.get("pk")=="report#3" for row in rows)
    assert guest.handler({"requestContext":{"http":{"method":"POST"}},"body":"[]"},None)["statusCode"]==400
    assert guest.handler({"requestContext":{"http":{"method":"POST"}},"body":json.dumps({"message":"x"*9000})},None)["statusCode"]==413
    print("PASS Lambda fixtures: escaping, pagination, API routing, and scheduled persistence")


if __name__ == "__main__":
    main()
