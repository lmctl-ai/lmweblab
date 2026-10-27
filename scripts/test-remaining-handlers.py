#!/usr/bin/env python3
"""Dependency-free regression tests for scenarios 07-09 handlers."""
import importlib.util, json, os, sys, unittest
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
        self.worker=load("scenarios/07-sqs-worker/lmaws/assets/worker.py","worker_test")
    def test_login_fail_closed_and_token(self):
        def call(body): return self.login.handler({"rawPath":"/login","requestContext":{"http":{"method":"POST"}},"body":json.dumps(body)})
        for body in ({"user":"unknown"},{"user":"unknown","password":""},{"user":"demo"},{"user":"demo","password":""}): self.assertEqual(call(body)["statusCode"],401)
        a=call({"user":"demo","password":"correct-horse"}); b=call({"user":"demo","password":"correct-horse"})
        self.assertEqual(a["statusCode"],200); self.assertNotEqual(a["headers"]["set-cookie"],b["headers"]["set-cookie"])
    def test_expiry_fixed_clock(self):
        os.environ["LMWEBLAB_NOW"]="100"; r=self.login.handler({"rawPath":"/login","requestContext":{"http":{"method":"POST"}},"body":"{\"user\":\"demo\",\"password\":\"correct-horse\"}"}); sid=r["headers"]["set-cookie"].split("=",1)[1].split(";",1)[0]
        os.environ["LMWEBLAB_NOW"]="111"; me=self.login.handler({"rawPath":"/me","requestContext":{"http":{"method":"GET"}},"headers":{"cookie":"sid="+sid}}); self.assertEqual(me["statusCode"],401)
    def test_shortener_rejects_bad_target(self):
        r=self.short.handler({"rawPath":"/links","requestContext":{"http":{"method":"POST"}},"body":"{\"code\":\"x\",\"target\":\"http://bad\"}"}); self.assertEqual(r["statusCode"],400)
    def test_worker_does_not_swallow_store_error(self):
        class Broken:
            def get_item(self, **_): return {}
            def put_item(self, **_): raise RuntimeError("store offline")
        self.fake.tables["lmaws_test"]=Broken()
        with self.assertRaises(RuntimeError): self.worker.handler({"Records":[{"messageId":"m","body":"{\"task\":\"x\"}"}]})

if __name__ == "__main__": unittest.main()
