# lmweblab Live Run Results

All live runs below were executed using **`AWS_PROFILE=lmaws`** only in `us-east-1`, with zero `aws` CLI usage (`lmcloud`, `lmcurl`, and `lmaws` only), and verified to leave **0 resources** behind. Sensitive account IDs, hosted zone IDs, distribution IDs, instance IDs, and caller IPs are omitted from committed files.

## Part B (`lmcloud` / OpenTofu v1.13.2, `lmcloud v0.1.12`)

### 1. Full Stack & Multi-Backend Live Runs

| Run ID | Scenario / Phase | Resources | `up.lms` Total (`init` / `plan` / `apply`) | `test.lms` Total | Key Measurements | `down.lms` Total (`destroy` / `audit`) | Leftovers (`tofu` + `lmaws` + DNS) | Est. Cost |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| `tfp1r2` | Phase 1 (HTTP: S3 + OAC + CloudFront + Route 53 Alias + EC2 Spot `t4g.nano`) | 14 | `232.35 s` (`0.97 s` / `3.51 s` / `227.87 s`) | `3.83 s` | `curl.load`: `p50 132.04 ms` / `p95 175.37 ms` / `p99 216.51 ms` | `281.03 s` (`276.16 s` / `4.86 s`) | **`0`** (`state_list=""`, `buckets=0`, `instances=0`, `sgs=0`) | `$0.0040` |
| `tfp2r2` | Phase 2 (ACM + HTTPS: adds ACM cert + Route 53 DNS validation CNAME + `redirect-to-https` custom alias) | 17 | `274.27 s` (`0.86 s` / `3.98 s` / `269.43 s`) | `4.53 s` | TLS cert chain PASS, `301` redirect PASS, `curl.load`: `p50 129.23 ms` / `p95 177.81 ms` / `p99 180.14 ms` | `328.76 s` (`314.80 s` / `13.96 s`) | **`0`** (`state_list=""`, post-destroy `plan add=17`, `buckets=0`, `instances=0`, `sgs=0`) | `$0.0040` |
| `s11r01` | [`11-weighted-dns-two-backends`](11-weighted-dns-two-backends/lmcloud/README.md) (Route 53 Weighted `A` across Static CloudFront + Dynamic EC2 Spot `t4g.nano`, shifting `90/10 -> 50/50 -> 0/100`) | 14 | `502.26 s` | `107.15 s` (`3` weight steps x `N=20` probes + `2` live `tofu.apply` weight updates) | `90/10` -> **`85% / 15%`** (`17/3`); `50/50` -> **`35% / 65%`** (`7/13`); `0/100` -> **`0% / 100%`** (`0/20`) | `284.69 s` (`276.03 s` / `8.55 s`) | **`0`** (`state_list=""`, post-destroy `plan add=14`, DNS `$.Answer` missing, `buckets=0`, `instances=0`, `sgs=0`) | `$0.0040` |
| `s03r02` | [`03-lambda-function-url-hello`](03-lambda-function-url-hello/lmcloud/README.md) (`LogGroup`, `Lambda`, `FunctionURL`, `LambdaPermission`, `CloudFront`, `Route53`) | 6 | `255.29 s` | `3.32 s` | Cold `664.97 ms`, Warm `238.85 ms`, CloudFront `385.87 ms`, Alias `260.02 ms`, `curl.load`: `p50 234.17 ms` / `p95 421.95 ms` / `p99 421.95 ms` | `321.53 s` (`314.04 s` / `7.28 s`) | **`0`** (`state_list=""`, post-destroy `plan add=6`, DNS `$.Answer` missing, `functions=0`, `log_groups=0`) | `$0.0001` |
| `s04r01` | [`04-lambda-dynamodb-guestbook`](04-lambda-dynamodb-guestbook/lmcloud/README.md) (`DynamoDB` PAY_PER_REQUEST + TTL, `LogGroup`, `Lambda`, `FunctionURL`, `LambdaPermission`) | 5 | `29.02 s` | `6.10 s` | Cold `598.31 ms`, Warm `590.70 ms`, `POST` `660.60 ms` / `491.70 ms` (XSS escaped + TTL), `GET` page1 `475.29 ms` / page2 `519.03 ms`, `curl.load`: `p50 492.71 ms` / `p95 656.60 ms` / `p99 656.60 ms` | `33.38 s` (`22.93 s` / `10.46 s`) | **`0`** (`state_list=""`, post-destroy `plan add=5`, `functions=0`, `tables=0`, `log_groups=0`) | `$0.0002` |
| `s05r02` | [`05-static-plus-api`](05-static-plus-api/lmcloud/README.md) (`S3` + BPA + Policy + Object, `OAC`, `LogGroup`, `Lambda`, `FunctionURL`, `LambdaPermission`, 2-Origin `CloudFront`, `Route53`) | 11 | `260.41 s` | `3.13 s` | Static `/` `304.98 ms` (`max-age=300`), `/api/status` Cold `537.26 ms` / Warm `427.36 ms` (`no-store`), `curl.load`: `p50 226.49 ms` / `p95 380.68 ms` / `p99 380.68 ms` | `284.24 s` (`274.13 s` / `9.96 s`) | **`0`** (`state_list=""`, post-destroy `plan add=11`, DNS `$.Answer` missing, `functions=0`, `buckets=0`, `log_groups=0`) | `$0.0005` |
| `s06r02` | [`06-scheduled-report`](06-scheduled-report/lmcloud/README.md) (`S3` + BPA, `DynamoDB`, `LogGroup`, `Lambda`, `FunctionURL`, `EventBridge Rule` + `Target`, 2 `LambdaPermission`s) | 10 | `33.13 s` | `44.30 s` | Cold `3,540.46 ms`, Warm `535.58 ms`, Manual `POST` `1,512.97 ms`, EventBridge `rate(1 minute)` observed (`2` runs in S3 + DDB, `GET` `580.62 ms`, HTML `584.09 ms`), `curl.load`: `p50 495.73 ms` / `p95 3,375.23 ms` | `49.56 s` (`29.75 s` / `19.80 s`) | **`0`** (`state_list=""`, post-destroy `plan add=10`, `functions=0`, `buckets=0`, `tables=0`, `log_groups=0`) | `$0.0002` |

### 2. Scenario 11 (`s11r01`) Live Weighted DNS Split Measurements (`lmcurl`, `N = 20` per step)

| Step | Target Weights (Static / Dynamic) | `tofu.apply` + Probe Time | Static Hits (CloudFront) | Dynamic Hits (EC2 Spot Nano) | Observed Split (Static % / Dynamic %) | Binomial Confidence Band (`N = 20`) | Result |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `90 / 10` | `4.42 s` (initial weights) | `17 / 20` | `3 / 20` | **`85% / 15%`** | Static in `[65%, 100%]` | **PASS** |
| 2 | `50 / 50` | `51.06 s` (incl. `tofu.apply` shift) | `7 / 20` | `13 / 20` | **`35% / 65%`** | Static in `[25%, 75%]` | **PASS** |
| 3 | `0 / 100` | `51.11 s` (incl. `tofu.apply` shift) | `0 / 20` | `20 / 20` | **`0% / 100%`** | Static in `[0%, 5%]` | **PASS** |

### 3. Scenario Catalog Verification Summary (`scenarios/`)

| Scenario | Engine | Offline `all.lms` Time | Planned Resources | Live Status / Evidence | Est. Cost |
| --- | --- | ---: | ---: | --- | ---: |
| [`01-static-site-s3-cloudfront`](01-static-site-s3-cloudfront/lmcloud/README.md) | `lmcloud` | `8.87 s` | 11 (HTTP) / 14 (ACM) | **LIVE PROVEN** in `tfp1r2` (HTTP) and `tfp2r2` (ACM + HTTPS), 0 leftovers | `$0.0005` live / `$0.0000` offline |
| [`02-dynamic-page-spot-nano`](02-dynamic-page-spot-nano/lmcloud/README.md) | `lmcloud` | `7.13 s` | 3 (SG + Spot `t4g.nano` + Route 53 `A`) | **LIVE PROVEN** in `tfp1r2`, `tfp2r2`, and `s11r01`, 0 leftovers | `$0.0035` live / `$0.0000` offline |
| [`03-lambda-function-url-hello`](03-lambda-function-url-hello/lmcloud/README.md) | `lmcloud` | `8.92 s` | 6 (`LogGroup`, `Lambda`, `FunctionURL`, `LambdaPermission`, `CloudFront`, `Route53`) | **LIVE PROVEN** in `s03r02` (`255.29 s` up / `3.32 s` test / `321.53 s` down, `p95 421.95 ms`), 0 leftovers | `$0.0001` live / `$0.0000` offline |
| [`04-lambda-dynamodb-guestbook`](04-lambda-dynamodb-guestbook/lmcloud/README.md) | `lmcloud` | `8.41 s` | 5 (`DynamoDB`, `LogGroup`, `Lambda`, `FunctionURL`, `LambdaPermission`) | **LIVE PROVEN** in `s04r01` (`29.02 s` up / `6.10 s` test / `33.38 s` down, `p95 656.60 ms`), 0 leftovers | `$0.0002` live / `$0.0000` offline |
| [`05-static-plus-api`](05-static-plus-api/lmcloud/README.md) | `lmcloud` | `9.15 s` | 11 (`S3` + BPA + Policy + Object, `OAC`, `LogGroup`, `Lambda`, `FunctionURL`, `LambdaPermission`, `CloudFront` 2-origin, `Route53`) | **LIVE PROVEN** in `s05r02` (`260.41 s` up / `3.13 s` test / `284.24 s` down, `p95 380.68 ms`), 0 leftovers | `$0.0005` live / `$0.0000` offline |
| [`06-scheduled-report`](06-scheduled-report/lmcloud/README.md) | `lmcloud` | `9.48 s` | 10 (`S3` + BPA, `DynamoDB`, `LogGroup`, `Lambda`, `FunctionURL`, `EventBridge Rule` + `Target`, 2 `LambdaPermission`s) | **LIVE PROVEN** in `s06r02` (`33.13 s` up / `44.30 s` test / `49.56 s` down, `p95 3,375.23 ms`), 0 leftovers | `$0.0002` live / `$0.0000` offline |
| [`11-weighted-dns-two-backends`](11-weighted-dns-two-backends/lmcloud/README.md) | `lmcloud` | `10.04 s` | 14 (`S3` + OAC + `CloudFront` + `SG` + Spot `t4g.nano` + 2 Route 53 weighted `A` records) | **LIVE PROVEN** in `s11r01` (`90/10 -> 50/50 -> 0/100`), 0 leftovers | `$0.0040` live / `$0.0000` offline |


## Part A: lmaws scenario engine

| Scenario | Verification | Up / test / down | Cost estimate | Own leftovers |
|---|---|---|---:|---:|
| 01 static site | Independent offline lifecycle; static contracts also passed as the static component of live 11 | See 11 for combined live timing | Included in 11 | 0 |
| 02 dynamic nano | Independent offline lifecycle; dynamic contracts and load also passed in live 11 | See 11 for combined live timing | Included in 11 | 0 |
| 11 weighted DNS | Live: 90/10 → 50/50 → 0/100, DoH/ECS sampling, all shared HTTP contracts | **335.062 / 126.615 / 496.019 s** | **$0.00312048** successful run | **0** |
| 03 Lambda hello | **LIVE verified**, including custom logs; see current campaign below | See live table | $0.00348786 | **0** |
| 04 guestbook | **LIVE verified**, including custom logs; see current campaign below | See live table | $0.00315286 | **0** |
| 05 static + API | **LIVE verified**, including custom logs; see current campaign below | See live table | $0.00349226 | **0** |
| 06 scheduled report | **LIVE verified**, including custom logs; see current campaign below | See live table | $0.00378932 | **0** |

The live run sampled **18 static / 2 dynamic**, **5 / 15**, and **0 / 20**. Load p95 was **221.47 ms**. Each sample result carries matching private run and live-mode fields. The complete campaign, including a cleaned failed readiness attempt, is conservatively estimated at **$0.00601854**, with zero active leftovers in both namespaces. Successful HTTP accounting charges the admitted 1000-request/10-MiB bound; no AWS invoice claim is made. [Sanitized numeric evidence](lmaws-results.json) contains no provider identifiers.

New source APIs have actual SDK loopback transport tests for Lambda/EventBridge/TTL/items/S3 notifications and CloudFront origin configuration. The role/PassRole grant is now active; the live Lambda campaign below is separate from offline fixture evidence. All live AWS interactions used profile `lmaws`; no AWS CLI, admin profile or permission changes were used.


## Remaining lmaws scenarios: live verification

Scenario 07 was excluded from this live GO; a separate authorization and confirmation of its mapping permissions are required. The authorized 08, 09, 10 and 12 campaign is complete.

| Scenario | Up / test / down including settlement (s) | p95 (ms) | Conservative estimate | Leftovers |
|---|---:|---:|---:|---:|
| 08 | 24.0 / 21.3 / 619.6 | 427.8 | $0.00325006 | **0** |
| 09 | 26.6 / 11.2 / 619.5 | 391.8 | $0.00325006 | **0** |
| 10 | 585.2 / 19.4 / 637.5 | 131.8 | $0.00364746 | **0** |
| 12 | 323.3 / 208.3 / 432.0 | 142.8 | $0.00334755 | **0** |

All four authorized lmaws scenarios passed live using only profile `lmaws`. Scenario 07 was not run live. Lambda functions used custom run-scoped log groups; down included the ten-minute final-log-delivery settlement. A fresh lmaws process then found zero leftovers across all eight attempt namespaces, including zero default Lambda log groups. The shared role, IAM, profiles and session files were untouched.

The p95 targets are the Function URL root for 08/09 (4 VUs, 16 requests, five-second window), the CloudFront gallery object for 10 (same load bound), and the dynamic app health endpoint for 12 (8 VUs, 10 requests). Initial/warm Function URL timings and the separate gallery fetch timings are in the sanitized summary. These are different request paths, not a controlled engine benchmark.

Scenario 08 verified login, authenticated cookie reads, logical TTL expiry and logout. Scenario 09 verified conditional creation/409, 301/302, missing-code 404 and atomic hit increments. Scenario 10 verified real signed PUT and CloudFront bytes/content type, plus changed type/length, oversized requests and expiry rejection. The tiny payload checks byte transport and declared MIME type; it does not decode images or generate thumbnails. Scenario 12 observed **0/20 → 20/0 → 0/20 static/dynamic hits**, proving manual cutover and return without health checks or automatic failover.

Recovered attempts remain in the cost and exit records: 08 exposed Function URL cookie-array handling and the need for strong authenticated reads; 10 exposed the exact web-bucket ownership name mismatch and JSON-double environment formatting; 12 exposed an endpoint-weight assertion before recursive DNS caches expired. That failed probe did not retain its counts; the corrected driver saves counts before assertions and waits beyond the 60-second TTL. Fixture checks now run in isolated copies and metrics have run-specific filenames. Scenario 09's original numeric readings were retained from the live monitor before a fixture check overwrote the former generic metric file; this limitation is explicit in the summary.

Campaign estimate, including all recovered attempts and final inventory calls: **$0.02382644**. These are conservative price-table estimates, not an AWS invoice. SDK request journals are combined with admitted HTTP/Lambda/log bounds and actual web compute/storage lifetime. Free-tier deductions are ignored. [Sanitized timings and cost evidence](lmaws-remaining-results.json); raw responses, resource identifiers and receipts stay private.

Local gates: lmaws `test.sh`, lmweblab `test.sh`, and `scenarios/test-remaining-lmaws.sh`; public pictures remain synthetic. No CI gate or private workflow dispatch was used.

## Current lmaws Lambda live campaign (session v6, boundary v2)

| Scenario | Up / test / cleanup + checks (s) | Cold / warm HTTP (ms) | p95 (ms) | Conservative estimate | Leftovers |
|---|---:|---:|---:|---:|---:|
| 03 | 297.4 / 5.3 / 397.8 | 422.5 / 224.9 | 285.0 | $0.00348786 | **0** |
| 04 | 32.3 / 3.8 / 74.0 | 1142.2 / 234.0 | 1058.8 | $0.00315286 | **0** |
| 05 | 269.8 / 2.8 / 310.1 | 437.1 / 248.8 | 340.6 | $0.00349226 | **0** |
| 06 | 36.2 / 103.6 / 58.9 | 1480.4 / 297.5 | 1151.2 | $0.00378932 | **0** |

[Sanitized structured evidence](lmaws-lambda-results.json). Scenario 06 observed two actual scheduled reports, four DynamoDB items (counter, latest, and two report rows), and both S3 artifacts.

Cold/warm timings are end-to-end Function URL responses on a fresh function, with the handler's cold-start indicator checked. Scenario 06 initially returns 404 because no scheduled report exists; those reads do not generate a report. Load uses four virtual users, sixteen requests, a five-second bounded window and a 2,000-ms p95 threshold.

Cleanup includes follow-up recovery/audit and post-delivery checks. Scenario 03's primary cleanup time is derived from the original command wall time minus up/test and includes orchestration overhead. Its first native cleanup pass failed before emergency cleanup completed; the original cause was not retained by that build. Scenario 04 required a fresh run after the one-second load window cut off concurrent cold starts; its successful run then exposed late untagged log-group recreation. These failures and their costs remain in the numeric evidence; the initial all-command exit codes are not rewritten as zero.

AWS can deliver Lambda logs 5–10 minutes after invocation. The final check ran after that window and found zero resources in all five attempt namespaces, including zero default `/aws/lambda/` groups. New `down` commands include bounded settlement. Only an exact group backed by the private run's creation receipt, provider creation timestamp and an absent function can have an empty tag set repaired; foreign-tagged, pre-existing or out-of-window groups are refused. IAM and the pre-created execution role were untouched. [AWS log-delivery guidance](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs.html).

Campaign estimate: **$0.01723215**, including the failed load-window attempt, SDK request journals and recovery checks. The model reserves 100 HTTP requests/2 MiB, the configured Lambda memory/timeout, 16 KiB of logs per request, and 20 scheduled invocations. It ignores free-tier deductions and is a conservative estimate, not an invoice. [Lambda pricing](https://aws.amazon.com/lambda/pricing/), [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/). Public pictures stay synthetic; raw live responses and identifiers remain ignored/private.
