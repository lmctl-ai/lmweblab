# Scenario 06 (`lmcloud` / OpenTofu): Scheduled Report (`EventBridge` -> `Lambda` -> `S3` + `DynamoDB`)

![Scenario 06 Architecture](images/s06_lmcloud_architecture.png)

`lmctl scenarios/06-scheduled-report/lmcloud/all.lms`

![Scenario 06 Report Runs](images/s06_lmcloud_runs.png)

`lmctl scenarios/06-scheduled-report/lmcloud/test.lms`

## Overview

Provisions an EventBridge scheduled rule (`rate(1 minute)`), a Python 3.12 Lambda function (`lmaws_tf_s06_<id>`) with Function URL, a private S3 reports bucket (`lmaws-tf-s06-<id>`), a DynamoDB runs ledger table (`lmaws_tf_s06_runs_<id>`), and a custom CloudWatch Log Group (`lmaws_tf_s06_logs_<id>`).

- **Typical cost**: `$0.0000` offline; `~$0.0002` per live run.
- **Typical time**: `~3.0s` offline; `33.1s` live `up`, `44.3s` live `test` (waiting for EventBridge `rate(1 minute)` trigger), `49.6s` live `down` (`0` leftovers).

## Live Run Results (`s06r02`, `AWS_PROFILE=lmaws`)

| Metric | Measured Value | Assertion Verified |
| --- | ---: | --- |
| `up.lms` (10 resources: `S3` + BPA, `DynamoDB`, `LogGroup`, `Lambda`, `FunctionURL`, `EventBridge Rule` + `Target`, 2 `LambdaPermission`s) | `33.13 s` (`33,128 ms`) | `tofu.apply` succeeded under `lmaws_session` v6 + `lmaws_lambda_exec` |
| Cold `GET /` | `3,540.46 ms` | `200 OK` (includes Python `boto3` + DynamoDB client init on 128 MB microVM) |
| Warm `GET /` | `535.58 ms` | `200 OK` |
| Manual `POST /` trigger (writes JSON + HTML to S3 + item to DynamoDB) | `1,512.97 ms` | `200 OK`, `scheduled_runs == 1` |
| EventBridge `rate(1 minute)` scheduled trigger poll (7 polls, ~30s) | `580.62 ms` (final `GET /`) | `eventbridge_runs >= 1`, `scheduled_runs == 2` |
| S3 HTML report fetch (`GET /?format=html`) | `584.09 ms` | `200 OK`, `reports/latest.html` rendered from S3 |
| 2-VU `curl.load` (`8` requests) `p50` / `p95` / `p99` | `495.73 ms` / `3,375.23 ms` / `3,375.23 ms` | `0.0%` error rate, `p95 < 5000 ms` PASS |
| `down.lms` (`tofu.destroy` `29.75 s` + `lmaws` audit `19.80 s`) | `49.56 s` (`49,555 ms`) | `state_list=""`, post-destroy `plan add=10`, `lmaws` `functions=0`, `buckets=0`, `tables=0`, `log_groups=0` |

## Commands

```bash
# Offline validation + plan + mock test + plot + diagram ($0.0000)
cd scenarios/06-scheduled-report/lmcloud
lmctl all.lms --offline

# Live lifecycle (AWS_PROFILE=lmaws only)
AWS_PROFILE=lmaws LMWEBLAB_LIVE=1 LMAWS_LIVE=1 lmctl all.lms --live --run-id s06r02
```
