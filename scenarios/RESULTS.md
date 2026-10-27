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
| 03 Lambda hello | Offline persistent lifecycle + real loopback handler HTTP/JSON and first/warm fixture calls | Fake only; no live timing | $0.00 offline | 0 simulated receipts |
| 04 guestbook | Offline lifecycle, POST/GET, escaping, cursor pagination, TTL field, bounded bodies, p95 | Fake only; no live timing | $0.00 offline | 0 simulated receipts |
| 05 static + API | Offline S3/Lambda origin wiring, `/` + `/api/*` handler routing and cache rules | Fake only; no live timing | $0.00 offline | 0 simulated receipts |
| 06 scheduled report | Offline rule wiring, repeated fixture invocations, cold-start-persistent counter and S3 JSON/HTML writes | Fake only; no real EventBridge schedule observed | $0.00 offline | 0 simulated receipts |

The live run sampled **18 static / 2 dynamic**, **5 / 15**, and **0 / 20**. Load p95 was **221.47 ms**. Each sample result carries matching private run and live-mode fields. The complete campaign, including a cleaned failed readiness attempt, is conservatively estimated at **$0.00601854**, with zero active leftovers in both namespaces. Successful HTTP accounting charges the admitted 1000-request/10-MiB bound; no AWS invoice claim is made. [Sanitized numeric evidence](lmaws-results.json) contains no provider identifiers.

New source APIs have actual SDK loopback transport tests for Lambda/EventBridge/TTL/items/S3 notifications and CloudFront origin configuration. The persistent serverless driver rejects live endpoints until explicit role/PassRole authorization. No live Lambda, DynamoDB guestbook or EventBridge success is implied by offline tests. All live AWS interactions used profile `lmaws`; no AWS CLI, admin profile or permission changes were used.


## Remaining lmaws scenarios — synthetic verification only

| Scenario | Offline result | Cleanup proof | Live state |
|---|---|---|---|
| [07 SQS worker](07-sqs-worker/lmaws/README.md) | Enqueue → deferred worker → conditional DynamoDB receipt; poison redrive after three receives | Repeat down; independent simulated queues/mapping/functions/logs/table audit: 0 | Pending Lead go and event-source mapping grant |
| [08 login](08-session-login-demo/lmaws/README.md) | Form asset, fail-closed credentials, random cookie, authenticated read, logical TTL expiry and logout | Repeat down; independent simulated audit: 0 | Pending Lead go |
| [09 shortener](09-url-shortener/lmaws/README.md) | Conditional create/409, 301/302, unknown 404, atomic counter; Decimal output regression fixed | Repeat down; independent simulated audit: 0 | Pending Lead go |
| [10 uploads](10-presigned-upload-gallery/lmaws/README.md) | Presign → PUT → exact-byte fetch; wrong type/length, oversize and expired grant rejected; separate host SDK SigV4 test | Repeat down; independent simulated audit: 0 | Pending Lead go; live CloudFront propagation unmeasured |
| [12 maintenance](12-maintenance-page-failover/lmaws/README.md) | Three all-or-nothing DNS targets persisted; lmcurl origin/cutover fixtures and picture report | Repeat down; independent simulated audit: 0 | Pending Lead go; not automatic health-check failover |

Gate: `scenarios/test-remaining-lmaws.sh`, including four handler unit regressions and live HTTP driver compilation/execution against loopback for 07–09. All new runs cost `$0.0000` offline. The [numeric synthetic receipts](remaining-offline-results.json) record elapsed times, two pictures per scenario and zero simulated leftovers; they contain no real provider data. The lmaws full local gate also passes real SDK loopback mapping/redrive, conditional-write and SigV4 header tests. No real subscription/account interaction, live timings, billing measurements or live zero-leftover claims were added. Existing live results above remain separate.
