#!/usr/bin/env python3
"""Dependency-free regression tests for scenarios 07-09 handlers."""
import importlib.util, json, os, sys, unittest
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scenarios/lib"))
from remaining_fake_boto3 import Boto3

def load(path, name):
    spec=importlib.util.spec_from_file_location(name, ROOT / path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.fake=Boto3(); sys.modules["boto3"]=self.fake
        os.environ.update({"LMWEBLAB_DEMO_PASSWORD":"correct-horse","TABLE_NAME":"lmaws_test","TTL_SECONDS":"10","RUN_ID":"test"})
        self.login=load("scenarios/08-session-login-demo/lmaws/assets/session_login.py","login_test")
        self.short=load("scenarios/09-url-shortener/lmaws/assets/url_shortener.py","short_test")
        self.api=load("scenarios/07-sqs-worker/lmaws/assets/api.py","api_test")
        self.worker=load("scenarios/07-sqs-worker/lmaws/assets/worker.py","worker_test")
    def test_login_fail_closed_and_token(self):
        def call(body): return self.login.handler({"rawPath":"/login","requestContext":{"http":{"method":"POST"}},"body":json.dumps(body)})
        for body in ({"user":"unknown"},{"user":"unknown","password":""},{"user":"demo"},{"user":"demo","password":""}): self.assertEqual(call(body)["statusCode"],401)
        a=call({"user":"demo","password":"correct-horse"}); b=call({"user":"demo","password":"correct-horse"})
        self.assertEqual(a["statusCode"],200); self.assertNotEqual(a["headers"]["set-cookie"],b["headers"]["set-cookie"])
    def test_expiry_fixed_clock(self):
        os.environ["LMWEBLAB_NOW"]="100"; r=self.login.handler({"rawPath":"/login","requestContext":{"http":{"method":"POST"}},"body":"{\"user\":\"demo\",\"password\":\"correct-horse\"}"}); sid=r["headers"]["set-cookie"].split("=",1)[1].split(";",1)[0]
        os.environ["LMWEBLAB_NOW"]="111"; me=self.login.handler({"rawPath":"/me","requestContext":{"http":{"method":"GET"}},"headers":{"cookie":"sid="+sid}}); self.assertEqual(me["statusCode"],401)

    def test_login_serializes_dynamodb_decimal(self):
        os.environ["LMWEBLAB_NOW"] = "100"
        self.fake.Table("lmaws_test").rows["s_decimal"] = {
            "pk": "s_decimal", "user": "demo", "expires_at": Decimal("200"), "run_id": "test"
        }
        me = self.login.handler({"rawPath":"/me", "requestContext":{"http":{"method":"GET"}}, "headers":{"cookie":"sid=s_decimal"}})
        self.assertEqual(me["statusCode"], 200)
        self.assertEqual(json.loads(me["body"])["expires_at"], 200)
    def test_function_url_cookie_array_and_strong_read(self):
        os.environ["LMWEBLAB_NOW"] = "100"
        class Table:
            def get_item(inner, **args):
                self.assertEqual(args["Key"], {"pk":"s_token"})
                self.assertIs(args.get("ConsistentRead"), True)
                return {"Item":{"user":"demo", "expires_at":Decimal("200")}}
        self.fake.tables["lmaws_test"] = Table()
        event={"rawPath":"/me", "requestContext":{"http":{"method":"GET"}}, "cookies":["sid=s_token", "sid=s_token"]}
        self.assertEqual(self.login.handler(event)["statusCode"],200)
        event["cookies"]=["sid=s_token", "sid=other"]
        self.assertEqual(self.login.handler(event)["statusCode"],401)

    def test_shortener_rejects_bad_target(self):
        r=self.short.handler({"rawPath":"/links","requestContext":{"http":{"method":"POST"}},"body":"{\"code\":\"x\",\"target\":\"http://bad\"}"}); self.assertEqual(r["statusCode"],400)

    def test_shortener_rejects_invalid_redirect_status(self):
        r=self.short.handler({"rawPath":"/links","requestContext":{"http":{"method":"POST"}},"body":"{\"code\":\"status\",\"target\":\"https://example.com/status\",\"status\":307}"})
        self.assertEqual(r["statusCode"], 400)
    def test_worker_is_idempotent_and_poison_is_not_stored(self):
        event={"Records":[{"messageId":"one","body":"{\"task\":\"report\"}"}]}
        self.assertEqual(self.worker.handler(event)["processed"],1)
        self.assertEqual(self.worker.handler(event)["processed"],0)
        poison=self.worker.handler({"Records":[{"messageId":"bad","body":"{\"task\":\"poison\"}"}]})
        self.assertEqual(poison["batchItemFailures"],[{"itemIdentifier":"bad"}])
        self.assertEqual(len(self.fake.Table("lmaws_test").rows),1)
    def test_api_does_not_enqueue_unknown_post_path(self):
        r=self.api.handler({"rawPath":"/unexpected","requestContext":{"http":{"method":"POST"}},"body":"{\"task\":\"report\"}"})
        self.assertEqual(r["statusCode"],404)

    def test_worker_does_not_swallow_store_error(self):
        class Broken:
            def get_item(self, **_): return {}
            def put_item(self, **_): raise RuntimeError("store offline")
        self.fake.tables["lmaws_test"]=Broken()
        with self.assertRaises(RuntimeError): self.worker.handler({"Records":[{"messageId":"m","body":"{\"task\":\"x\"}"}]})

if __name__ == "__main__": unittest.main()
