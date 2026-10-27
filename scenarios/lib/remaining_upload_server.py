"""Bounded loopback adapter for the actual upload Lambda handler plus fake S3."""
import base64, importlib.util, json, os, sys, threading, time, types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from remaining_fake import Boto3
ROOT=Path(__file__).resolve().parents[1]
fake=Boto3();sys.modules['boto3']=fake
config=types.ModuleType('botocore.config');config.Config=lambda **kwargs:kwargs
sys.modules['botocore']=types.ModuleType('botocore');sys.modules['botocore.config']=config
spec=importlib.util.spec_from_file_location('gallery',ROOT/'10-presigned-upload-gallery/lmaws/assets/gallery.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
ready,stop=map(Path,sys.argv[1:3])
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_): pass
    def send(self,status,body=b'',mime='application/json'):
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def call(self,method,body=''):
        try:
            result=module.handler({'requestContext':{'http':{'method':method}},'rawPath':urlparse(self.path).path,'body':body},None)
            data=base64.b64decode(result['body']) if result.get('isBase64Encoded') else result['body'].encode()
            self.send(result['statusCode'],data,result.get('headers',{}).get('content-type','application/json'))
        except Exception: self.send(500,b'{"error":"handler failed"}')
    def do_POST(self):
        n=int(self.headers.get('Content-Length','0'))
        if n>8192:self.send(413);return
        self.call('POST',self.rfile.read(n).decode())
    def do_PUT(self):
        p=urlparse(self.path);n=int(self.headers.get('Content-Length','0'));g=fake.s3.grants.get(parse_qs(p.query).get('token',[''])[0])
        if not g or p.path!='/s3/'+g[1] or fake.s3.now()>g[4] or n!=g[3] or self.headers.get('Content-Type')!=g[2]:self.send(403);return
        data=self.rfile.read(n);fake.s3.put_object(Bucket=g[0],Key=g[1],Body=data,ContentType=g[2]);self.send(200)
    def do_GET(self):
        if urlparse(self.path).path=='/__expire':fake.s3.offset+=901;self.send(204);return
        self.call('GET')
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);os.environ['UPLOAD_ENDPOINT']=f'http://127.0.0.1:{server.server_port}'
ready.write_text(os.environ['UPLOAD_ENDPOINT']);threading.Thread(target=server.serve_forever,daemon=True).start();deadline=time.monotonic()+120
try:
    while not stop.exists() and time.monotonic()<deadline:time.sleep(.05)
finally:server.shutdown();server.server_close()
