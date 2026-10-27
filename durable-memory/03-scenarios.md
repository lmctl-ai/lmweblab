# Scenario catalog: lmaws engine

Start with `scenarios/README.md`, `COMPARE.md` and `RESULTS.md`. Each implementation lives in `scenarios/NN-name/lmaws/` and is run from that directory. Five entry points: up, test, down, status, all. `all` collects child failures before always invoking down. The original combined `lmaws/web_stack.lms` remains available.

01 is S3/OAC/CloudFront/ACM plus a Route 53 alias. 02 is only a nano and its SG/A record. 11 composes both and shifts weighted DNS 90/10 → 50/50 → 0/100. Common scalar configuration and native calls live in `scenarios/lib/lmaws.lms`. Assets and base HTTP contracts remain in root `shared/`. Installed compiler 0.2.426 rejects const, so entry points use uppercase let; no list splices are required.

All live work uses profile lmaws, region us-east-1, fresh hexadecimal run IDs, own tags and private state. State, logs, ledgers, effective config, HTTP target files and receipts are ignored. Configuration files include the run ID so separate invocations cannot replace another run's settings. Do not execute fixture tests in a directory with an active deployment: use the isolated `scenarios/test-lmaws.sh` gate.

Weighted records have an exact run-scoped name, stable static/dynamic identifiers, and matching current-run targets. Initial CREATE refuses preexisting records. Shifts wait INSYNC. lmcurl samples via DoH with distinct ECS /24 subnets and explicit resolve; tests use an outward-rounded three-sigma binomial band and require zero static hits at zero weight. Cleanup discovers all exact-name records and refuses foreign ones.

03–06 are offline only until the Lead explicitly authorizes Lambda live tests. The execution role must be exactly lmaws_lambda_exec; no tests use admin or change IAM. Future live tests must verify actual resource persistence, schedules, provider propagation and cleanup rather than extrapolating from loopback fixtures.

Run `test.sh` for the base stack and `scenarios/test-lmaws.sh` for isolated scenario lifecycles. New APIs require a current source-built lmaws executable on PATH until released. Every HTTP contract uses lmcurl; no AWS CLI is permitted.
