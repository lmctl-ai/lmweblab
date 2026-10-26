# lmweblab Live Run Results

All live runs below were executed using **`AWS_PROFILE=lmaws`** only in `us-east-1`, with zero `aws` CLI usage (`lmcloud`, `lmcurl`, and `lmaws` only), and verified to leave **0 resources** behind. Sensitive account IDs, hosted zone IDs, distribution IDs, instance IDs, and caller IPs are omitted from committed files.

## Part B (`lmcloud` / OpenTofu v1.13.2, `lmcloud v0.1.12`)

### 1. Full Stack & Multi-Backend Live Runs

| Run ID | Scenario / Phase | Resources | `up.lms` Total (`init` / `plan` / `apply`) | `test.lms` Total | Key Measurements | `down.lms` Total (`destroy` / `audit`) | Leftovers (`tofu` + `lmaws` + DNS) | Est. Cost |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| `tfp1r2` | Phase 1 (HTTP: S3 + OAC + CloudFront + Route 53 Alias + EC2 Spot `t4g.nano`) | 14 | `232.35 s` (`0.97 s` / `3.51 s` / `227.87 s`) | `3.83 s` | `curl.load`: `p50 132.04 ms` / `p95 175.37 ms` / `p99 216.51 ms` | `281.03 s` (`276.16 s` / `4.86 s`) | **`0`** (`state_list=""`, `buckets=0`, `instances=0`, `sgs=0`) | `$0.0040` |
| `tfp2r2` | Phase 2 (ACM + HTTPS: adds ACM cert + Route 53 DNS validation CNAME + `redirect-to-https` custom alias) | 17 | `274.27 s` (`0.86 s` / `3.98 s` / `269.43 s`) | `4.53 s` | TLS cert chain PASS, `301` redirect PASS, `curl.load`: `p50 129.23 ms` / `p95 177.81 ms` / `p99 180.14 ms` | `328.76 s` (`314.80 s` / `13.96 s`) | **`0`** (`state_list=""`, post-destroy `plan add=17`, `buckets=0`, `instances=0`, `sgs=0`) | `$0.0040` |
| `s11r01` | [`11-weighted-dns-two-backends`](11-weighted-dns-two-backends/lmcloud/README.md) (Route 53 Weighted `A` across Static CloudFront + Dynamic EC2 Spot `t4g.nano`, shifting `90/10 -> 50/50 -> 0/100`) | 14 | `502.26 s` | `107.15 s` (`3` weight steps x `N=20` probes + `2` live `tofu.apply` weight updates) | `90/10` -> **`85% / 15%`** (`17/3`); `50/50` -> **`35% / 65%`** (`7/13`); `0/100` -> **`0% / 100%`** (`0/20`) | `284.69 s` (`276.03 s` / `8.55 s`) | **`0`** (`state_list=""`, post-destroy `plan add=14`, DNS `$.Answer` missing, `buckets=0`, `instances=0`, `sgs=0`) | `$0.0040` |

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
| [`03-lambda-function-url-hello`](03-lambda-function-url-hello/lmcloud/README.md) | `lmcloud` | `8.92 s` | 6 (`LogGroup`, `Lambda`, `FunctionURL`, `OAC`, `CloudFront`, `Route53`) | **OFFLINE VERIFIED** (`tofu.validate` + `tofu.plan` + `lmcurl` mock + `lmplot` + `lmdraw`); awaiting `lmaws_lambda_exec` role | `$0.0001` live / `$0.0000` offline |
| [`04-lambda-dynamodb-guestbook`](04-lambda-dynamodb-guestbook/lmcloud/README.md) | `lmcloud` | `8.41 s` | 4 (`DynamoDB`, `LogGroup`, `Lambda`, `FunctionURL`) | **OFFLINE VERIFIED** (`tofu.validate` + `tofu.plan` + `lmcurl` mock + `lmplot` + `lmdraw`); awaiting `lmaws_lambda_exec` role | `$0.0002` live / `$0.0000` offline |
| [`05-static-plus-api`](05-static-plus-api/lmcloud/README.md) | `lmcloud` | `9.15 s` | 10 (`S3` + BPA + Policy + Object, `OAC`, `LogGroup`, `Lambda`, `FunctionURL`, `CloudFront` 2-origin, `Route53`) | **OFFLINE VERIFIED** (`tofu.validate` + `tofu.plan` + `lmcurl` mock + `lmplot` + `lmdraw`); awaiting `lmaws_lambda_exec` role | `$0.0005` live / `$0.0000` offline |
| [`06-scheduled-report`](06-scheduled-report/lmcloud/README.md) | `lmcloud` | `9.48 s` | 9 (`S3` + BPA, `DynamoDB`, `LogGroup`, `Lambda`, `FunctionURL`, `EventBridge Rule` + `Target`, `LambdaPermission`) | **OFFLINE VERIFIED** (`tofu.validate` + `tofu.plan` + `lmcurl` mock + `lmplot` + `lmdraw`); awaiting `lmaws_lambda_exec` role | `$0.0002` live / `$0.0000` offline |
| [`11-weighted-dns-two-backends`](11-weighted-dns-two-backends/lmcloud/README.md) | `lmcloud` | `10.04 s` | 14 (`S3` + OAC + `CloudFront` + `SG` + Spot `t4g.nano` + 2 Route 53 weighted `A` records) | **LIVE PROVEN** in `s11r01` (`90/10 -> 50/50 -> 0/100`), 0 leftovers | `$0.0040` live / `$0.0000` offline |
