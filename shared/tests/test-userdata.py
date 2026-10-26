#!/usr/bin/env python3
"""Run the actual user-data HTTP handler through lmcurl on loopback only."""
from __future__ import annotations

import http.server
import os
import pathlib
import re
import shutil
import tempfile
import threading


ROOT = pathlib.Path(__file__).resolve().parents[2]
USERDATA = ROOT / "shared" / "userdata" / "user_data.sh"
RUN_ID = "fixture-a1b2c3d4"


def load_handler() -> type[http.server.BaseHTTPRequestHandler]:
    source = USERDATA.read_text(encoding="utf-8")
    match = re.search(r"cat >/usr/local/bin/lmweblab_server\.py <<'PYEOF'\n(.*?)\nPYEOF", source, re.S)
    if not match:
        raise AssertionError("user-data server heredoc was not found")
    namespace = {"__name__": "lmweblab_userdata_fixture"}
    os.environ["LMWEBLAB_RUN_ID"] = RUN_ID
    os.environ["LMWEBLAB_PORT"] = "0"
    exec(compile(match.group(1), str(USERDATA), "exec"), namespace)
    return namespace["WebServer"], namespace["Handler"]


def main() -> None:
    server_type, handler = load_handler()
    server = server_type(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="lmweblab-userdata-") as temporary:
            work = pathlib.Path(temporary)
            tests = ROOT / "shared" / "tests"
            shutil.copy(tests / "dynamic_contract.lms", work / "dynamic_contract.lms")
            load_source = (tests / "load_check.lms").read_text(encoding="utf-8")
            load_source = load_source.replace(
                "assert(load.p95_ms()>=0.0);assert(load.error_rate()==0.0);assert(load.p95_ms()<5000.0);",
                'println("load metrics requests="+str(load.requests())+" p95="+str(load.p95_ms())+" errors="+str(load.error_rate()));assert(load.p95_ms()>=0.0);assert(load.error_rate()==0.0);assert(load.p95_ms()<5000.0);',
            )
            (work / "load_check.lms").write_text(load_source, encoding="utf-8")
            (work / ".lmweblab-dynamic-url").write_text(f"http://127.0.0.1:{server.server_port}", encoding="utf-8")
            env = dict(os.environ, LMWEBLAB_RUN_ID=RUN_ID, LMWEBLAB_LIVE="1", AWS_PROFILE="lmaws", AWS_DEFAULT_PROFILE="lmaws", AWS_REGION="us-east-1", AWS_EC2_METADATA_DISABLED="true")
            for script in ("dynamic_contract.lms", "load_check.lms"):
                result = __import__("subprocess").run(["lmctl", script, "--live"], cwd=work, env=env, text=True, capture_output=True, timeout=180)
                if result.returncode:
                    if script == "load_check.lms":
                        # Keep the failing load metrics in the exception so a
                        # transport regression is diagnosable without a second
                        # network client.
                        detail = result.stdout + result.stderr
                    else:
                        detail = result.stdout + result.stderr
                    raise AssertionError(f"{script} failed:\n{detail}")
            print("PASS user-data Python handler through lmcurl: escaped echo, API counter/time, run id and zero-error p95 load")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
