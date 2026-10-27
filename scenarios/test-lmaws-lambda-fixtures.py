#!/usr/bin/env python3
"""Exercise the committed Lambda handlers without AWS credentials."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    guest = load(ROOT / "04-lambda-dynamodb-guestbook/lmaws/assets/guestbook.py", "guestbook")
    os.environ["TABLE_NAME"] = "lmaws_s04_fixture"
    first = guest.handler({"requestContext": {"http": {"method": "POST"}}, "body": json.dumps({"author": "A <b>", "message": "<script>alert(1)</script>"})}, None)
    assert first["statusCode"] == 201
    body = json.loads(first["body"])
    assert "&lt;script&gt;" in body["entry"]["message"]
    page = guest.handler({"requestContext": {"http": {"method": "GET"}}, "queryStringParameters": {"limit": "1", "offset": "0"}}, None)
    assert page["statusCode"] == 200 and json.loads(page["body"])["total"] == 1

    api = load(ROOT / "05-static-plus-api/lmaws/assets/api.py", "api")
    response = api.handler({"rawPath": "/api/info", "queryStringParameters": {"q": "fixture"}}, None)
    assert response["statusCode"] == 200 and json.loads(response["body"])["path"] == "/api/info"

    reporter = load(ROOT / "06-scheduled-report/lmaws/assets/reporter.py", "reporter")
    one = json.loads(reporter.handler({}, None)["body"])
    two = json.loads(reporter.handler({}, None)["body"])
    assert one["scheduled_runs"] == 1 and two["scheduled_runs"] == 2
    print("PASS Lambda fixtures: escaping, pagination, API routing, and scheduled persistence")


if __name__ == "__main__":
    main()
