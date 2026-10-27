# Scenario 05: Unified CloudFront (`/` -> S3, `/api/*` -> Lambda URL) (`lmcloud`)

![Scenario 05 Architecture](images/s05_lmcloud_architecture.png)

`lmctl scenarios/05-static-plus-api/lmcloud/all.lms`

![Scenario 05 Latency](images/s05_lmcloud_latency.png)

`lmctl scenarios/05-static-plus-api/lmcloud/test.lms`

## Overview

Deploys a single-domain web application with zero CORS requirements by routing two origins behind one CloudFront distribution (`lmaws-tf-s05-site-<id>.<domain>`):
- **Default cache behavior (`/*`)**: Private S3 bucket (`lmaws-tf-s05-<id>`) via CloudFront Origin Access Control (OAC SigV4) with `Cache-Control: public, max-age=300`.
- **Ordered cache behavior (`/api/*`)**: Python 3.12 Lambda Function URL (`lmaws_tf_s05_<id>`) with `TTL=0` (`Cache-Control: no-store`) and custom CloudWatch Log Group (`lmaws_tf_s05_logs_<id>`).

- **Typical cost**: `$0.0000` offline; `~$0.0005` per live run.
- **Typical time**: `~2.5s` offline; `260.4s` live `up`, `3.1s` live `test`, `284.2s` live `down` (`0` leftovers).

## Live Run Results (`s05r02`, `AWS_PROFILE=lmaws`)

| Metric | Measured Value | Assertion Verified |
| --- | ---: | --- |
| `up.lms` (11 resources: `S3` + BPA + Policy + Object, `OAC`, `LogGroup`, `Lambda`, `FunctionURL`, `LambdaPermission`, `CloudFront` 2-origin, `Route53`) | `260.41 s` (`260,412 ms`) | `tofu.apply` succeeded under `lmaws_session` v6 + `lmaws_lambda_exec` |
| Static `GET /index.html` (CloudFront -> S3 OAC) | `304.98 ms` | `200 OK`, `"lmweblab Static Site"`, `Cache-Control: public, max-age=300` |
| Dynamic Cold `GET /api/status?check=1` (CloudFront -> Lambda URL) | `537.26 ms` | `200 OK`, `service == "lmweblab-s05-static-plus-api"`, `Cache-Control: no-store` |
| Dynamic Warm `GET /api/status?check=2` (CloudFront -> Lambda URL) | `427.36 ms` | `200 OK`, `cold_start == false`, `Cache-Control: no-store` |
| Route 53 Alias `GET /index.html` + `GET /api/status` | PASS | Both static and dynamic routes served on `lmaws-tf-s05-site-<id>.<domain>` without CORS |
| 4-VU `curl.load` (`16` requests to `/api/status`) `p50` / `p95` / `p99` | `226.49 ms` / `380.68 ms` / `380.68 ms` | `0.0%` error rate, `p95 < 5000 ms` PASS |
| `down.lms` (`tofu.destroy` + DNS + `lmaws` audit) | `284.24 s` (`284,238 ms`) | `state_list=""`, post-destroy `plan add=11`, DNS `$.Answer` missing, `lmaws` `functions=0`, `buckets=0`, `log_groups=0` |

## Commands

```bash
# Offline validation + mock test + diagram/chart ($0.0000)
cd scenarios/05-static-plus-api/lmcloud
lmctl all.lms --offline

# Live AWS run (AWS_PROFILE=lmaws only)
AWS_PROFILE=lmaws LMWEBLAB_DOMAIN=example.com LMWEBLAB_LIVE=1 LMAWS_LIVE=1 lmctl all.lms --live --run-id s05r02
```
