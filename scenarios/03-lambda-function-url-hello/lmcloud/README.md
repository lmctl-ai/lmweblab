# Scenario 03: Lambda Function URL + CloudFront + Route 53 (`lmcloud`)

![Scenario 03 Architecture](images/s03_lmcloud_architecture.png)

`lmctl scenarios/03-lambda-function-url-hello/lmcloud/all.lms`

![Scenario 03 Latency](images/s03_lmcloud_latency.png)

`lmctl scenarios/03-lambda-function-url-hello/lmcloud/test.lms`

## Overview

Deploys a Python 3.12 Lambda function (`lmaws_tf_s03_<id>`) with a custom CloudWatch Log Group (`lmaws_tf_s03_logs_<id>`), a public Function URL (`authorization_type = "NONE"` + `FunctionURLAllowPublicInvoke`), a CloudFront distribution with the Function URL as custom HTTPS origin (`TTL=0`), and a Route 53 alias `A` record (`lmaws-tf-s03-api-<id>.<domain>`).

- **Typical cost**: `$0.0000` offline; `~$0.0001` per live run.
- **Typical time**: `~2.5s` offline; `255.3s` live `up`, `3.3s` live `test`, `321.5s` live `down` (`0` leftovers).

## Live Run Results (`s03r02`, `AWS_PROFILE=lmaws`)

| Metric | Measured Value | Assertion Verified |
| --- | ---: | --- |
| `up.lms` (6 resources: `LogGroup`, `Lambda`, `FunctionURL`, `LambdaPermission`, `CloudFront`, `Route53`) | `255.29 s` (`255,292 ms`) | `tofu.apply` succeeded under `lmaws_session` v6 + `lmaws_lambda_exec` |
| Direct Function URL Cold `GET /?name=DirectCold` | `664.97 ms` | `200 OK`, JSON schema valid, `greeting == "Hello, DirectCold!"`, `cold_start == true` |
| Direct Function URL Warm `GET /?name=DirectWarm` | `238.85 ms` | `200 OK`, JSON schema valid, `cold_start == false` |
| CloudFront Edge `GET /?name=CloudFront` | `385.87 ms` | `200 OK`, JSON schema valid, `greeting == "Hello, CloudFront!"` |
| Route 53 Alias `GET /?name=Route53Alias` | `260.02 ms` | `200 OK`, JSON schema valid, `greeting == "Hello, Route53Alias!"` |
| 4-VU `curl.load` (`16` requests via CloudFront) `p50` / `p95` / `p99` | `234.17 ms` / `421.95 ms` / `421.95 ms` | `0.0%` error rate, `p95 < 5000 ms` PASS |
| `down.lms` (`tofu.destroy` `314.04 s` + DNS + `lmaws` audit `7.28 s`) | `321.53 s` (`321,528 ms`) | `state_list=""`, post-destroy `plan add=6`, DNS `$.Answer` missing, `lmaws` `functions=0`, `log_groups=0` |

## Commands

```bash
# Offline validation + mock test + diagram/chart ($0.0000)
cd scenarios/03-lambda-function-url-hello/lmcloud
lmctl all.lms --offline

# Live AWS run (AWS_PROFILE=lmaws only)
AWS_PROFILE=lmaws LMWEBLAB_DOMAIN=example.com LMWEBLAB_LIVE=1 LMAWS_LIVE=1 lmctl all.lms --live --run-id s03r02
```
