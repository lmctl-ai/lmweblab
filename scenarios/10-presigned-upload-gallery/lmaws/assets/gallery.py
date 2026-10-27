"""Bounded presigned PUT demo. Declared MIME type is signed, not image decoding."""
import base64
import json
import os
import re
import boto3
from botocore.config import Config

MAX_BYTES = max(1, min(int(os.getenv("MAX_UPLOAD_BYTES", "1048576")), 1048576))
EXPIRY_SECONDS = max(1, min(int(os.getenv("UPLOAD_EXPIRY_SECONDS", "300")), 900))
ALLOWED = {"image/png", "image/jpeg", "image/webp", "image/gif"} & set(os.getenv("CONTENT_TYPES", "image/png,image/jpeg,image/webp,image/gif").split(","))
BUCKET = os.getenv("BUCKET_NAME", "lmaws-fixture-gallery")

def reply(status, body):
    return {"statusCode": status, "headers": {"content-type": "application/json", "cache-control": "no-store"}, "body": json.dumps(body)}

def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/")
    if method == "POST" and path == "/presign":
        try:
            raw = event.get("body") or "{}"
            if event.get("isBase64Encoded"): raw = base64.b64decode(raw, validate=True).decode()
            if len(raw) > 4096: return reply(413, {"error": "request too large"})
            req = json.loads(raw)
            key, mime, size = req["key"], req["content_type"], req["size"]
            if not isinstance(key, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}\.(png|jpg|jpeg|webp|gif)", key): return reply(400, {"error": "key"})
            if mime not in ALLOWED: return reply(415, {"error": "content_type"})
            if type(size) is not int or not 1 <= size <= MAX_BYTES: return reply(413, {"error": "size"})
        except (KeyError, TypeError, ValueError): return reply(400, {"error": "request"})
        url = boto3.client("s3", config=Config(signature_version="s3v4")).generate_presigned_url(
            "put_object", Params={"Bucket": BUCKET, "Key": key, "ContentType": mime, "ContentLength": size}, ExpiresIn=EXPIRY_SECONDS, HttpMethod="PUT")
        return reply(200, {"url": url, "key": key, "expires_in": EXPIRY_SECONDS, "content_type": mime, "content_length": size})
    if method == "GET" and path.startswith("/gallery/"):
        key = path.removeprefix("/gallery/")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}\.(png|jpg|jpeg|webp|gif)", key): return reply(400, {"error": "key"})
        try: obj = boto3.client("s3").get_object(Bucket=BUCKET, Key=key)
        except boto3.client("s3").exceptions.NoSuchKey: return reply(404, {"error": "not found"})
        data = obj["Body"].read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES: return reply(413, {"error": "size"})
        return {"statusCode": 200, "headers": {"content-type": obj.get("ContentType", "application/octet-stream")}, "isBase64Encoded": True, "body": base64.b64encode(data).decode()}
    return reply(404, {"error": "not found"})
