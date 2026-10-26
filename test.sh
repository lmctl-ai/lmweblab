#!/usr/bin/env bash
set -euo pipefail
root_dir="$(cd "$(dirname "$0")" && pwd)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/lmweblab-gate.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT
cp -R "$root_dir/lmaws" "$root_dir/shared" "$work_dir/"
cd "$work_dir"
export LMWEBLAB_LIVE=0 LMAWS_LIVE=0 LMWEBLAB_DOMAIN=example.com AWS_EC2_METADATA_DISABLED=true
unset LMWEBLAB_RUN_ID
# Supply a current lmaws executable on PATH, or allow lmctl to install the released host.
timeout 300 lmctl lmaws/web_stack.lms all --offline --phase2
timeout 180 lmctl lmaws/test_recipes.lms
timeout 180 lmctl lmaws/report.lms
timeout 180 python3 shared/tests/test-userdata.py
python3 - <<'PY'
from pathlib import Path
for name in ('lmaws_architecture','lmaws_latency'):
    picture=Path('images')/(name+'.png')
    assert picture.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'),picture
    assert picture.stat().st_size<=300000,picture
print('PASS offline stack, both HTTP contract phases, teardown and synthetic pictures; AWS untouched')
PY
