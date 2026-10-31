#!/usr/bin/env python3
"""Exercise live HTTP contracts on loopback only; no AWS credentials or writes."""
from pathlib import Path
import os,sys,tempfile,subprocess,time,json
root=Path(__file__).resolve().parents[1]
for number in ['03','04','05','06']:
 with tempfile.TemporaryDirectory(prefix='sv-http-proof-') as directory:
  work=Path(directory);(work/'.lmweblab-local').mkdir();ready=work/'ready';stop=work/'stop'
  env=dict(os.environ,RUN_ID='demo01',AWS_PROFILE='lmaws',AWS_EC2_METADATA_DISABLED='true')
  server=subprocess.Popen([sys.executable,str(root/'scenarios/lib/lambda_fixture_server.py'),number,str(ready),str(stop)],cwd=work,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  try:
   for _ in range(500):
    if ready.exists():break
    if server.poll() is not None:raise AssertionError(server.stderr.read().decode())
    time.sleep(.01)
   url=ready.read_text().strip();script=work/'contract.lms'
   prefix=''
   if number=='06':
    prefix='''let tick=_dsl_ cli="lmcurl";
let s=curl.session('''+json.dumps(url)+''');let a=s.get("/fixture/tick").send();let b=s.get("/fixture/tick").send();assert_eq(a.status(),200);assert_eq(b.status(),200);
end _dsl_
savedsl(tick,"tick.dslb");assert(system(concat(dsl_cli(tick),["--lmcode","tick.dslb"]),30000).code==0);
'''
   script.write_text('import '+json.dumps(str(root/'scenarios/lib/serverless_http.lms'))+';\n'+prefix+'let o={number:'+json.dumps(number)+',live:true,run_id:"demo01",timeout_ms:5000,samples:4,p95_ms:"2000.0"};\nlet meta={lambda_url:'+json.dumps(url)+',cf_url:'+json.dumps(url)+',site_url:'+json.dumps(url)+'};\nlet first=sl_first_invokes(o,meta);let result=sl_http_test(o,meta);\n')
   p=subprocess.run(['lmctl',str(script)],cwd=work,env=env,capture_output=True,text=True,timeout=120)
   if p.returncode:raise AssertionError(p.stdout+p.stderr+'\n'+ '\n'.join(f.read_text() for f in (work/'.lmweblab-local').glob('*.log')))
   print('PASS actual lmcurl contract against local production handler:',number)
  finally:
   stop.touch()
   try:server.wait(timeout=5)
   except subprocess.TimeoutExpired:server.kill();server.wait()
