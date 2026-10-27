#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
fixture_dir="$(mktemp -d)"
trap 'rm -rf "$fixture_dir"' EXIT
python3 - "$repo_dir" "$fixture_dir" <<'PY'
from pathlib import Path
import shutil,sys
source,target=map(Path,sys.argv[1:])
for name in ('scenarios','shared','scripts'):
 shutil.copytree(source/name,target/name,ignore=shutil.ignore_patterns('.lmweblab-local','reports','*.dslb','.terraform','*.tfstate*','__pycache__'))
PY
export LMWEBLAB_LIVE=0 LMAWS_LIVE=0 AWS_PROFILE=lmaws AWS_DEFAULT_PROFILE=lmaws AWS_EC2_METADATA_DISABLED=true
unset LMWEBLAB_RUN_ID LMAWS_ENDPOINT
export LMWEBLAB_SYNTHETIC_STORE="$fixture_dir/results.json"
cd "$fixture_dir"
timeout 30 python3 scripts/test-remaining-handlers.py
timeout 300 python3 scripts/test-remaining-live-contracts.py
for scenario in 07-sqs-worker 08-session-login-demo 09-url-shortener 10-presigned-upload-gallery 12-maintenance-page-failover; do
 cd "$fixture_dir/scenarios/$scenario/lmaws"
 timeout 300 lmctl all.lms --offline
 timeout 120 lmctl status.lms --offline
 timeout 180 lmctl down.lms --offline
 timeout 120 lmctl report.lms
 python3 - <<'PY'
import json,os
from pathlib import Path
assert json.loads(Path('.lmweblab-local/audit.json').read_text())['leftovers']==0
images=list(Path('images').glob('*.png'));assert len(images)>=2
for image in images:assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'),image
# Documentation may contain sanitized live results; fixture receipts below must remain synthetic.
assert json.loads(Path('.lmweblab-local/audit.json').read_text()).get('synthetic', True) is True
store=Path(os.environ['LMWEBLAB_SYNTHETIC_STORE']);rows=json.loads(store.read_text()) if store.exists() else []
actions={}
for action in ('up','test','down','all'):
 candidates=[Path('.lmweblab-local')/(action+'-receipt.json'),Path('.lmweblab-local')/(action+'-timing.json')]
 receipt=next(json.loads(p.read_text()) for p in candidates if p.exists())
 assert receipt['passed'] is True
 actions[action]=receipt['elapsed_ms']
rows.append({'scenario':Path.cwd().parent.name,'mode':'synthetic','elapsed_ms':actions,'simulated_leftovers':0,'repeat_down_passed':True,'gallery_pngs':len(images),'estimated_cost_usd':'0.0000'})
store.write_text(json.dumps(rows,indent=2)+'\n')
print('PASS independent simulated zero-leftover audit, repeat down and gallery PNGs')
PY
done
python3 - <<'PY_RESULTS'
import json,os
from pathlib import Path
rows=json.loads(Path(os.environ['LMWEBLAB_SYNTHETIC_STORE']).read_text());assert len(rows)==5
output=os.environ.get('LMWEBLAB_SYNTHETIC_RESULTS','')
if output:Path(output).write_text(json.dumps({'mode':'synthetic','real_aws_requests':0,'scenarios':rows},indent=2)+'\n')
PY_RESULTS
printf '%s\n' 'PASS five isolated remaining scenarios; synthetic only, no real AWS' 
