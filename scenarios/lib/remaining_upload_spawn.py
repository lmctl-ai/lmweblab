import subprocess, sys, time
from pathlib import Path
server = Path(__file__).with_name("remaining_upload_server.py")
ready, stop = sys.argv[1], sys.argv[2]
subprocess.Popen([sys.executable, str(server), ready, stop], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(200):
    if Path(ready).exists(): break
    time.sleep(0.01)
if not Path(ready).exists(): raise SystemExit("scenario 10 fixture server did not publish readiness")
