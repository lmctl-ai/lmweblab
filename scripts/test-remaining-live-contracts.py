#!/usr/bin/env python3
"""Compile and execute the live HTTP drivers against loopback handlers, never AWS."""
import json, os, subprocess, sys, time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for number,name in [('07','sqs-worker'),('08','session-login-demo'),('09','url-shortener')]:
    directory=root/f'scenarios/{number}-{name}/lmaws';state=directory/'.lmweblab-local';state.mkdir(exist_ok=True)
    token=str(time.time_ns());ready=state/(token+'.url');stop=state/(token+'.stop')
    env=dict(os.environ,TABLE_NAME='lmaws_worker',TTL_SECONDS='1',LMWEBLAB_DEMO_PASSWORD='correct-horse',AWS_EC2_METADATA_DISABLED='true')
    env.pop('LMWEBLAB_NOW',None)
    server=subprocess.Popen([sys.executable,str(root/'scenarios/lib/remaining_fixture_server.py'),number,str(ready),str(stop)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for _ in range(200):
            if ready.exists():break
            if server.poll() is not None:raise AssertionError(server.stderr.read().decode())
            time.sleep(.01)
        assert ready.exists(),'fixture readiness timed out'
        config={'number':number,'url':ready.read_text().strip(),'ttl_seconds':1}
        driver=directory/f'.lmweblab-local/live-contract-{number}.lms'
        # Resolve the shared helper relative to the private driver directory.
        driver.write_text('import "../../../lib/remaining_live.lms";\nrw_live_test('+json.dumps(config)+');\n')
        run=subprocess.run(['lmctl',str(driver)],cwd=directory,env=env,capture_output=True,text=True,timeout=180)
        assert run.returncode==0,(number,run.stdout,run.stderr)
        print('PASS live HTTP driver compiled and exercised on synthetic loopback:',number)
    finally:
        stop.touch()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
