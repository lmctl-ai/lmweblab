#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
sandbox_dir="$(mktemp -d)"
trap 'rm -rf "$sandbox_dir"' EXIT
python3 - "$repo_dir" "$sandbox_dir" <<'PY_COPY'
import shutil,sys
from pathlib import Path
source,target=map(Path,sys.argv[1:])
for name in ('scenarios','shared'):
    shutil.copytree(source/name,target/name,ignore=shutil.ignore_patterns('.lmweblab-local','reports','*.dslb','.lmweblab-*-url','.terraform','*.tfstate*','__pycache__'))
PY_COPY
export LMWEBLAB_LIVE=0 LMAWS_LIVE=0 AWS_EC2_METADATA_DISABLED=true LMWEBLAB_DOMAIN=example.com
unset LMWEBLAB_RUN_ID
for scenario_name in 01-static-site-s3-cloudfront 02-dynamic-page-spot-nano 11-weighted-dns-two-backends; do
  cd "$sandbox_dir/scenarios/$scenario_name/lmaws"
  timeout 300 lmctl all.lms --offline
  timeout 120 lmctl report.lms
  python3 - <<'PY'
import json
from pathlib import Path
assert json.loads(Path('.lmweblab-local/audit.json').read_text())['leftovers']==0
for image in ('architecture','results'):
    assert Path(f'images/{image}.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
PY
done
for scenario_name in 03-lambda-function-url-hello 04-lambda-dynamodb-guestbook 05-static-plus-api 06-scheduled-report; do
  cd "$sandbox_dir/scenarios/$scenario_name/lmaws"
  timeout 300 lmctl all.lms --offline
  timeout 120 lmctl status.lms --offline
  timeout 120 lmctl down.lms --offline
  python3 - <<'PY_LAMBDA'
import json
from pathlib import Path
assert json.loads(Path('.lmweblab-local/status.json').read_text())['status']=='down'
images=list(Path('images').glob('*.png'))
assert len(images)>=2
for image in images: assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'),image
PY_LAMBDA
done
cd "$sandbox_dir"
timeout 120 python3 scenarios/test-lmaws-lambda-fixtures.py
printf '%s\n' 'PASS seven isolated lmaws scenario lifecycles, HTTP fixtures, status, repeat down and pictures; no live AWS'
