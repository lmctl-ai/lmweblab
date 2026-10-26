#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
sandbox_dir="$(mktemp -d)"
trap 'rm -rf "$sandbox_dir"' EXIT
cp -R "$repo_dir/scenarios" "$repo_dir/shared" "$sandbox_dir/"
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
printf '%s\n' 'PASS isolated lmaws scenario lifecycles and pictures; no live AWS'
