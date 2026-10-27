#!/usr/bin/env python3
"""Start the loopback Lambda fixture server detached from lmscript."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

scenario, ready, stop = sys.argv[1:4]
server = Path(__file__).with_name("lambda_fixture_server.py")
subprocess.Popen([sys.executable, str(server), scenario, ready, stop], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
for _ in range(200):
    if Path(ready).exists():
        break
    time.sleep(0.01)
if not Path(ready).exists():
    raise SystemExit("fixture server did not publish readiness")
