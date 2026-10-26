#!/usr/bin/env bash
set -euo pipefail

# Reproducible local gate: no AWS profile, URLs, credentials, or network calls
# are used by the examples. lmctl may download the pinned lmcurl host once.
root_dir="$(cd "$(dirname "$0")/../.." && pwd)"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/lmweblab-offline.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT
mkdir -p "$tmp_dir/shared/tests"
cp "$root_dir"/shared/tests/{static_contract,dynamic_contract,load_check}.lms "$tmp_dir/shared/tests/"
touch "$tmp_dir/.lmweblab-offline"
for script in static_contract dynamic_contract load_check; do
  (cd "$tmp_dir" && timeout 180 lmctl "shared/tests/${script}.lms")
done
printf 'lmweblab offline lmcurl gate passed (AWS untouched)\n'
