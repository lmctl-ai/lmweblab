# lmweblab Part B (`lmcloud` / OpenTofu) — Comparison, Live Timings & Engineering Notes

## 1. Live Run Summary (Phase 1 HTTP, Phase 2 ACM + HTTPS, Scenario 11 Weighted DNS)

All live runs executed end-to-end under the single least-privilege session profile **`AWS_PROFILE=lmaws`** in `us-east-1` with **no `aws` CLI** (`lmcloud`, `lmcurl`, and `lmaws` only), followed by complete teardown (`down.lms`) and independent `lmaws` zero-leftover verification.

| Phase / Metric | Phase 1 (`tfp1r2`, HTTP, 14 resources) | Phase 2 (`tfp2r2`, ACM + HTTPS, 17 resources) | Scenario 11 (`s11r01`, Weighted DNS, 14 resources) | Notes |
| --- | ---: | ---: | ---: | --- |
| Caller `/32` IP detection (`lmcurl`) | `181 ms` (`0.18 s`) | `242 ms` (`0.24 s`) | `215 ms` (`0.22 s`) | `https://checkip.amazonaws.com` |
| `tofu.fmt_check` + `tofu.init` + `tofu.validate` | `973 ms` (`0.97 s`) | `863 ms` (`0.86 s`) | `912 ms` (`0.91 s`) | Shared plugin cache + `.h1` hash sidecar (`lmcloud v0.1.11+`) |
| `tofu.plan` (live Route 53 + SSM lookups) | `3,506 ms` (`3.51 s`) | `3,978 ms` (`3.98 s`) | `3,640 ms` (`3.64 s`) | Phase 1 & S11: `14 to add`; Phase 2: `17 to add` |
| `tofu.apply` (incl. CloudFront `Deployed`) | `227,870 ms` (`227.87 s`) | `269,429 ms` (`269.43 s`) | `497,497 ms` (`497.50 s`) | CloudFront edge propagation + initial Route 53 weighted `90/10` INSYNC wait |
| **Total `up.lms`** | **`232,350 ms` (`3m 52.4s`)** | **`274,272 ms` (`4m 34.3s`)** | **`502,264 ms` (`8m 22.3s`)** | |
| **Total `test.lms`** (incl. `lmdraw` + `lmplot`) | **`3,828 ms` (`3.83 s`)** | **`4,529 ms` (`4.53 s`)** | **`107,148 ms` (`1m 47.1s`)** | S11 includes 2 live `tofu.apply` Route 53 weight shifts (`50/50` and `0/100`, ~46s INSYNC each) + 60 DoH/HTTP probes |
| `tofu.destroy` (incl. CloudFront disable+delete + Spot fallback) | `276,161 ms` (`276.16 s`) | `314,800 ms` (`314.80 s`) | `276,025 ms` (`276.03 s`) | Verifies `tofu.state_list == ""` and post-destroy `tofu.plan` add count (`14` / `17` / `14`) |
| Independent `lmaws` + DNS leftover audit | `4,863 ms` (`4.86 s`) | `13,958 ms` (`13.96 s`) | `8,547 ms` (`8.55 s`) | **0 leftovers** in all 3 live runs (S11 also verifies DNS `$.Answer` is missing) |
| **Total `down.lms`** | **`281,026 ms` (`4m 41.0s`)** | **`328,762 ms` (`5m 28.8s`)** | **`284,694 ms` (`4m 44.7s`)** | **`leftovers_count: 0`** |
| **Estimated Run Cost** | **`$0.0040`** | **`$0.0040`** | **`$0.0040`** | Spot `t4g.nano` (~8–14 min) + 8 GiB `gp3` + public IPv4 + S3/CF/R53 requests |

---

## 2. Live HTTP / HTTPS / Weighted DNS Measurements (`lmcurl`)

| Metric | Phase 1 (`tfp1r2`, HTTP) | Phase 2 (`tfp2r2`, ACM + HTTPS) | Scenario 11 (`s11r01`, Weighted DNS) | Assertion Verified |
| --- | ---: | ---: | ---: | --- |
| CloudFront `GET /index.html` (`https://d....cloudfront.net`) | `165.57 ms` | `228.96 ms` | PASS (`Backend A`) | `200 OK`, body match, `Cache-Control: public, max-age=300` |
| CloudFront custom `404` (`GET /nonexistent-path-404.html`) | `352.92 ms` | `376.82 ms` | N/A | `404 Not Found`, custom `/404.html` body |
| Custom domain `https://lmaws-tf-site-<id>.<domain>` | N/A (Phase 1 tested via `http://` + `Host`) | `200 OK` (TLS verified) | N/A | X.509 certificate subject matches `lmaws-tf-site-<id>.<domain>`, valid chain, `301` redirect from `http://` |
| Dynamic EC2 Spot nano `GET /?echo=dns_ok` | `132.99 ms` | `218.06 ms` | PASS (`Backend B`) | `200 OK`, HTML-escaped query (`<script>alert(1)</script>` -> `&lt;script&gt;...`), `run_id` present |
| `curl.load` (4 virtual users, 20 requests to `/api/info`) p50 / p95 / p99 | `132.04 / 175.37 / 216.51 ms` | `129.23 / 177.81 / 180.14 ms` | N/A | `0.0%` error rate, `p95 < 5000 ms` PASS |
| Weighted DNS Step 1 (`90/10`, `N=20`) | N/A | N/A | **`85% Static / 15% Dynamic`** (`17 / 3`) | Within binomial band `[65%, 100%]` |
| Weighted DNS Step 2 (`50/50`, `N=20`) | N/A | N/A | **`35% Static / 65% Dynamic`** (`7 / 13`) | Within binomial band `[25%, 75%]` |
| Weighted DNS Step 3 (`0/100`, `N=20`) | N/A | N/A | **`0% Static / 100% Dynamic`** (`0 / 20`) | Within binomial band `[0%, 5%]` |

---

## 3. `lmcloud` and `lmscript` Issues Found & Fixed

### A. `lmcloud v0.1.11` — Shared Provider Plugin Cache & `.h1` Sidecar Hash Cache
- **Problem**: `hashicorp/aws` v5.100.0 is a ~165 MB download that unpacks to a **707 MB** binary (`terraform-provider-aws_v5.100.0_x5`). Without a shared plugin cache, every new OpenTofu directory re-downloaded `hashicorp/aws`; even with `TF_PLUGIN_CACHE_DIR`, OpenTofu's `PackageHashV1` re-read and SHA-256 hashed all 707 MB (~1.8s–3s of disk I/O) on every `tofu.init(dir)`.
- **Fix in `/home/mma/repos/dsl/lmcloud` (`v0.1.11`)**:
  1. Configured `<UserCacheDir>/lmcloud/plugin-cache` by default in `internal/lmhost/host.go` (overrideable via `LMCLOUD_PLUGIN_CACHE_DIR` or `TF_PLUGIN_CACHE_DIR`) with `PluginCacheMayBreakDependencyLockFile = true`.
  2. Added a sidecar `<packageDir>.h1` hash cache in `internal/getproviders/hash.go` keyed by `(size, mtime_ns, mode)` alongside `<packageDir>.lock`.
  3. Added `Dir.CachedVersions` in `internal/providercache/dir.go` and an offline fallback in `internal/providercache/installer.go` so `tofu.init` works offline from the shared cache.
- **Result**: `tofu.init` + `tofu.validate` with `hashicorp/aws` dropped from ~120s cold to **`0.86s`–`0.97s`** warm across fresh scenario directories.

### B. `lmcloud v0.1.12` — Least-Privilege EC2 Spot Instance Teardown (`CancelSpotInstanceRequests` Fallback)
- **Problem**: When `aws_instance` is launched with `instance_market_options { market_type = "spot" }`, `terraform-provider-aws` stores `spot_instance_request_id` and `instance_market_options` in `terraform.tfstate`. On `tofu.destroy(dir)`, `terraform-provider-aws` calls `ec2:CancelSpotInstanceRequests` on `arn:aws:ec2:us-east-1:<account>:spot-instances-request/sir-...` **before** calling `ec2:TerminateInstances` on the instance. Because `ec2:RunInstances` does not tag the implicit `spot-instances-request` and the `lmaws_session` policy linter rightly forbids unscoped write actions, `CancelSpotInstanceRequests` fails with `403 UnauthorizedOperation`.
- **Fix in `/home/mma/repos/dsl/lmcloud` (`v0.1.12`, commit `d28deb0953`)**:
  - Updated `Host.Destroy(dir)` in `internal/lmhost/host.go`: when `ApplyCommand{Destroy: true}` fails with `CancelSpotInstanceRequests` in `stderr`, `clearSpotRequestIDs` clears `spot_instance_request_id`, `instance_market_options`, and `instance_lifecycle` in `<dir>/terraform.tfstate` and retries `ApplyCommand{Destroy: true}` with `-refresh=false`.
  - `terraform-provider-aws` then proceeds directly to `ec2:TerminateInstances` on the tagged instance, which terminates the instance and automatically closes its one-time Spot request on AWS's side.
  - Added unit test `TestClearSpotRequestIDs` in `internal/lmhost/host_test.go` and documented this as the supported route for least-privilege sessions in `durable-memory/04-gotchas.md`.

### C. IAM Session Policy (`lmaws_session`) Findings Discovered & Resolved with Lead
1. **Security group default egress & Spot request tag conditions (pre-run review)**:
   - AWS automatically creates a default outbound `0.0.0.0/0` egress rule on `ec2:CreateSecurityGroup`, so `terraform-provider-aws` requires `ec2:RevokeSecurityGroupEgress` / `ec2:AuthorizeSecurityGroupEgress` on tagged security groups; and `ec2:RunInstances` cannot pass `aws:RequestTag/lmaws_test` on the implicit `network-interface` and `spot-instances-request` resource types.
2. **CloudFront `cloudfront:CreateDistribution` alongside `CreateDistributionWithTags` (Phase 1 Run 1)**:
   - When `terraform-provider-aws` calls `CreateDistributionWithTags`, CloudFront's IAM evaluator checks **both** `cloudfront:CreateDistributionWithTags` and `cloudfront:CreateDistribution` under `aws:RequestTag/lmaws_test`. Fixed in `lmaws_session` v3.
3. **ACM `acm:GetCertificate` when CloudFront attaches a custom certificate (Phase 2 Run 1)**:
   - When `aws_cloudfront_distribution` specifies `viewer_certificate.acm_certificate_arn`, CloudFront makes a cross-service call to ACM using the caller's session for `acm:GetCertificate` on the tagged certificate (`aws:ResourceTag/lmaws_test`). Fixed in `lmaws_session` v5.

### D. `lmscript` `${NAME}` Interpolation Bug Report: Whole-Valued Floats Emit as `int` Literals

When a top-level LMScript number has no fractional part (such as `2.0` or `5000.0`), JavaScript's IEEE-754 `Number` representation does not distinguish `2.0` from `2`. When `${NAME}` splices that value into a typed `_dsl_` (`_lmcode_`) block, `lmscript` formats it as an integer literal (`2`), causing type-checking errors on host methods whose schema requires `float`.

- **Exact minimal failing reproducer (`repro_float_interp.lms`)**:
  ```lms
  let DURATION_S = 2.0;
  let THRESHOLD_MS = 5000.0;
  let p = _dsl_ cli="lmcurl";
  assert_close(${DURATION_S}, ${THRESHOLD_MS}, 10000.0);
  end _dsl_
  ```
- **Command**:
  ```sh
  lmscript --check repro_float_interp.lms
  ```
- **Actual output**:
  ```text
  error:repro_float_interp.lms:4:14: _lmcode_: function assert_close expects float for argument 1; found int
  ```
  (Same error on `curl.load(req, 4, ${DURATION_S}, 20)` -> `_lmcode_: method Curl.load expects float for argument 3; found int`.)
- **Expected behavior**:
  Either:
  1. `_lmcode_` type checking should implicitly widen `int` literals (`2`, `5000`) to `float` when a parameter expects `float` (just as HCL/C/Go/TypeScript widen integer constants or as `_lmcode_` could coerce `int -> float`), **or**
  2. `lmscript` could provide a `float_lit(x)` helper / preserve `.0` when splicing into a `float` parameter position.
- **Current workaround in scenarios**:
  Store float constants as strings (`let LOAD_DURATION_S = "2.0";`) and convert inside `_dsl_` via `str_to_float(${LOAD_DURATION_S})` (or `float(${INT_CONST})` where `float()` is in the host's stdlib).

---

## 4. What Was Awkward in OpenTofu for These Stacks

1. **Five-Resource Chain for a Single HTTPS Static Site**:
   - Attaching HTTPS to a CloudFront distribution in OpenTofu requires coordinating 5 separate resources across 3 AWS services (`aws_acm_certificate`, `aws_route53_record` for DNS validation, `aws_acm_certificate_validation` waiter, `aws_cloudfront_distribution`, and `aws_route53_record` alias), plus conditional `count = var.enable_acm ? 1 : 0` indexing on every reference.
2. **CloudFront Default Certificate vs `aliases` Exclusivity**:
   - CloudFront rejects `CreateDistributionWithTags` if `aliases` is non-empty while `cloudfront_default_certificate = true`. Phase 1 (HTTP) and Scenario 11 (`backend-a-static`) must set `aliases = []` on the distribution even when a Route 53 alias `A` record points to it, requiring callers over HTTP to send `Host: d....cloudfront.net` (which both Backend A CloudFront and Backend B Python `http.server` accept on `/index.html`).
3. **Route 53 Weighted Alias vs Weighted `A` Record Schema Differences (`Scenario 11`)**:
   - In `aws_route53_record`, a weighted record pointing to CloudFront (`backend-a-static`) uses an `alias { ... }` block with **no** `ttl` or `records` attributes (Route 53 inherits CloudFront's 60s alias TTL), whereas the sibling weighted record on the exact same `name` pointing to the EC2 Spot nano public IPv4 (`backend-b-dynamic`) uses `ttl = 60` and `records = [aws_instance.app.public_ip]` with **no** `alias` block. Both share `name = lmaws-tf-split-<id>.<domain>` and `type = "A"` and differ by `weighted_routing_policy { weight = ... }` and `set_identifier`.
4. **Measuring Route 53 Weighted Splits Without OS Stub-Resolver Caching (`Scenario 11`)**:
   - Because Route 53 weighted records return a single answer per DNS query with a 60s TTL, calling `curl.session("http://lmaws-tf-split-<id>.<domain>")` 20 times in a tight loop hits the local OS stub resolver cache and sends all 20 requests to whichever backend won the first DNS lookup.
   - Pairing a DNS-over-HTTPS query (`https://dns.google/resolve?name=<fqdn>&type=A&edns_client_subnet=70.<step>.<i>.0/24`) with `lmcurl`'s `.resolve(fqdn + ":80:" + ip)` on each request cleanly samples Route 53's authoritative weighted distribution across distinct `/24` client subnets without waiting 60 seconds between every single HTTP request.
5. **AWS Lambda Function URL Dual-Permission Requirement in `terraform-provider-aws` v5.100.0 (`Scenarios 03, 04, 05, 06`)**:
   - When `aws_lambda_function_url` is created with `authorization_type = "NONE"`, `terraform-provider-aws` v5.100.0 only adds `lambda:InvokeFunctionUrl` (`Principal = "*"`, `FunctionUrlAuthType = "NONE"`). However, AWS Lambda now enforces **both** `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` (`Principal = "*"`) on public Function URLs, returning `403 AccessDeniedException` unless an explicit `aws_lambda_permission` resource (`action = "lambda:InvokeFunction"`, `principal = "*"`, `statement_id = "FunctionURLAllowPublicInvoke"`) is also declared alongside `aws_lambda_function_url`.
6. **Custom `logging_config` + Pre-Created CloudWatch Log Group Required for Least-Privilege Sessions & Clean Teardown (`Scenarios 03, 04, 05, 06`)**:
   - By default, AWS Lambda lazily creates `/aws/lambda/<function_name>` on first invocation, which falls outside `arn:aws:logs:*:*:log-group:lmaws_*` in `lmaws_session` / `lmaws_boundary` and is orphaned when `aws_lambda_function` is destroyed.
   - Declaring an explicit `aws_cloudwatch_log_group` named `lmaws_tf_<slug>_logs_<id>` and referencing it via `logging_config { log_format = "Text", log_group = aws_cloudwatch_log_group.fn.name }` ensures (a) `lmaws_lambda_exec` can write logs under `lmaws_boundary` v2, and (b) OpenTofu's dependency graph creates the log group before the function and deletes the function before deleting the log group on `tofu.destroy`.
7. **CloudFront Origin Domain Formatting for Lambda Function URLs (`Scenarios 03, 05`)**:
   - `aws_lambda_function_url.api.function_url` returns a full URL (`https://<id>.lambda-url.us-east-1.on.aws/`), whereas `aws_cloudfront_distribution` `origin.domain_name` rejects schemes and trailing slashes (`replace(replace(aws_lambda_function_url.api.function_url, "https://", ""), "/", "")`).

---

## 5. Live Lambda Scenarios 03, 04, 05, and 06 — Timings, Latencies & IAM Verification (`lmaws_session` v6)

All four Lambda scenarios (`03`, `04`, `05`, `06`) were executed **LIVE** under `AWS_PROFILE=lmaws` (`lmaws_session` v6 + `lmaws_lambda_exec` with `lmaws_boundary` v2) and torn down with **0 leftovers**:

| Scenario | Run ID | Resources | `up.lms` | Cold Invoke | Warm Invoke | `test.lms` Total | `curl.load` (`p50` / `p95` / `p99`) | `down.lms` (`destroy` / `audit`) | Leftovers | Est. Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [`03-lambda-function-url-hello`](03-lambda-function-url-hello/lmcloud/README.md) | `s03r02` | 6 | `255.29 s` | `664.97 ms` | `238.85 ms` (`CF 385.87 ms`, `Alias 260.02 ms`) | `3.32 s` | `234.17` / `421.95` / `421.95 ms` | `321.53 s` (`314.04 s` / `7.28 s`) | **`0`** | `$0.0001` |
| [`04-lambda-dynamodb-guestbook`](04-lambda-dynamodb-guestbook/lmcloud/README.md) | `s04r01` | 5 | `29.02 s` | `598.31 ms` | `590.70 ms` (`POST 660.60 ms`, `GET 475.29 ms`) | `6.10 s` | `492.71` / `656.60` / `656.60 ms` | `33.38 s` (`22.93 s` / `10.46 s`) | **`0`** | `$0.0002` |
| [`05-static-plus-api`](05-static-plus-api/lmcloud/README.md) | `s05r02` | 11 | `260.41 s` | `537.26 ms` (`/api/status`) | `427.36 ms` (`Static / 304.98 ms`) | `3.13 s` | `226.49` / `380.68` / `380.68 ms` | `284.24 s` (`274.13 s` / `9.96 s`) | **`0`** | `$0.0005` |
| [`06-scheduled-report`](06-scheduled-report/lmcloud/README.md) | `s06r02` | 10 | `33.13 s` | `3,540.46 ms` (128 MB `boto3` init) | `535.58 ms` (`POST 1,512.97 ms`, `HTML 584.09 ms`) | `44.30 s` (incl. `rate(1 minute)` EventBridge wait) | `495.73` / `3,375.23` / `3,375.23 ms` | `49.56 s` (`29.75 s` / `19.80 s`) | **`0`** | `$0.0002` |

### IAM Action Matrix Verified Live Under `lmaws_session` v6 (`terraform-provider-aws` v5.100.0)

| OpenTofu Resource / Data Source | Scenarios | Resource ARN / Pattern | Exact IAM Actions Called by `terraform-provider-aws` | Status in `lmaws_session` v5 & Notes for Live Run |
| --- | --- | --- | --- | --- |
| `data.aws_caller_identity.current` | 03, 04, 05, 06 | `*` | `sts:GetCallerIdentity` | **Already Allowed** (`Sid: Reads`). Used to construct `arn:aws:iam::<account>:role/lmaws_lambda_exec` without calling `iam:GetRole` (which `lmaws_session` forbids). |
| `aws_cloudwatch_log_group.fn` | 03, 04, 05, 06 | `arn:aws:logs:us-east-1:<account>:log-group:lmaws_tf_s0*` (`*` for `DescribeLogGroups`) | `logs:CreateLogGroup`, `logs:PutRetentionPolicy`, `logs:DescribeLogGroups`, `logs:ListTagsForResource`, `logs:TagResource`, `logs:DeleteLogGroup` | **Already Allowed** (`Sid: Reads` + `Sid: NamedTestResources` on `arn:aws:logs:*:*:log-group:lmaws_*`). Note: Our `.tf` configs set `logging_config { log_group = "lmaws_tf_<slug>_logs_<id>" }` on `aws_lambda_function` so Lambda does not create an untagged `/aws/lambda/...` log group outside `lmaws_*`. |
| `aws_dynamodb_table` | 04, 06 | `arn:aws:dynamodb:us-east-1:<account>:table/lmaws_tf_s0*` | `dynamodb:CreateTable`, `dynamodb:DescribeTable`, `dynamodb:DescribeContinuousBackups`, `dynamodb:DescribeTimeToLive`, `dynamodb:UpdateTimeToLive`, `dynamodb:ListTagsOfResource`, `dynamodb:TagResource`, `dynamodb:DeleteTable` | **Already Allowed** (`Sid: NamedTestResources` grants `dynamodb:*` on `arn:aws:dynamodb:*:*:table/lmaws_*`). |
| `aws_s3_bucket`, `aws_s3_bucket_public_access_block`, `aws_s3_bucket_policy`, `aws_s3_object` | 05, 06 | `arn:aws:s3:::lmaws-tf-s0*` and `arn:aws:s3:::lmaws-tf-s0*/*` | `s3:CreateBucket`, `s3:PutBucketTagging`, `s3:PutBucketPublicAccessBlock`, `s3:PutBucketPolicy`, `s3:PutObject`, `s3:Get*`, `s3:ListBucket`, `s3:DeleteObject`, `s3:DeleteBucket` | **Already Allowed & Live-Proven** (`Sid: NamedTestResources`). |
| `aws_cloudfront_origin_access_control`, `aws_cloudfront_distribution`, `aws_route53_record` | 03, 05 | `arn:aws:cloudfront::<account>:distribution/*`, `arn:aws:route53:::hostedzone/*` (`lmaws-*.<domain>`) | `cloudfront:CreateOriginAccessControl`, `cloudfront:CreateDistributionWithTags`, `cloudfront:CreateDistribution`, `cloudfront:TagResource`, `cloudfront:Get*`, `cloudfront:Update*`, `cloudfront:Delete*`, `route53:ChangeResourceRecordSets`, `route53:GetChange` | **Already Allowed & Live-Proven** (`lmaws_session` v3/v5). |
| `aws_lambda_function` | 03, 04, 05, 06 | `arn:aws:lambda:us-east-1:<account>:function:lmaws_tf_s0*` + role `arn:aws:iam::<account>:role/lmaws_lambda_exec` | `iam:PassRole` (with `iam:PassedToService = lambda.amazonaws.com`), `lambda:CreateFunction`, `lambda:GetFunction`, `lambda:GetFunctionConfiguration`, `lambda:GetFunctionCodeSigningConfig`, `lambda:ListVersionsByFunction`, `lambda:ListTags`, `lambda:TagResource`, `lambda:UpdateFunctionCode`, `lambda:UpdateFunctionConfiguration`, `lambda:DeleteFunction` | **Requires Lambda + PassRole grant**: Needs (1) `lambda:*` on `arn:aws:lambda:*:*:function:lmaws-*` and `arn:aws:lambda:*:*:function:lmaws_*`, and (2) `iam:PassRole` on `arn:aws:iam::*:role/lmaws_*` conditioned on `StringEquals: {"iam:PassedToService": "lambda.amazonaws.com"}`. (`terraform-provider-aws` reads function state via `lambda:GetFunction` and `lambda:ListVersionsByFunction` on the function ARN; it does not require `lambda:ListFunctions` on `*`.) |
| `aws_lambda_function_url` | 03, 04, 05, 06 | `arn:aws:lambda:us-east-1:<account>:function:lmaws_tf_s0*` | `lambda:CreateFunctionUrlConfig`, `lambda:GetFunctionUrlConfig`, `lambda:UpdateFunctionUrlConfig`, `lambda:DeleteFunctionUrlConfig`, plus `lambda:AddPermission` (`FunctionURLAllowPublicAccess`), `lambda:GetPolicy`, `lambda:RemovePermission` | Covered by `lambda:*` on `arn:aws:lambda:*:*:function:lmaws_*`. (When `authorization_type = "NONE"`, `terraform-provider-aws` automatically calls `lambda:AddPermission` / `lambda:GetPolicy` / `lambda:RemovePermission` on the function ARN.) |
| `aws_cloudwatch_event_rule`, `aws_cloudwatch_event_target`, `aws_lambda_permission` | 06 | `arn:aws:events:us-east-1:<account>:rule/lmaws_tf_s06_rule_*` | `events:PutRule`, `events:DescribeRule`, `events:ListTagsForResource`, `events:TagResource`, `events:PutTargets`, `events:ListTargetsByRule`, `events:RemoveTargets`, `events:DeleteRule`, plus `lambda:AddPermission` / `lambda:GetPolicy` / `lambda:RemovePermission` | **Requires EventBridge (`events:*`) in `NamedTestResources`**: Add `"events:*"` to `Action` and `"arn:aws:events:*:*:rule/lmaws-*"`, `"arn:aws:events:*:*:rule/lmaws_*"` to `Resource` in `Sid: NamedTestResources` of `lmaws_session`. |


## lmaws scenario engine (Part A)

Scenarios 01 and 02 split the original native-host stack into independent deployments, using the same root `shared/site`, `shared/userdata` and lmcurl contracts as the base project. Scenario 11 composes both backends and adds weighted DNS. The scripts use scalar interpolation and uppercase `let` because installed LMScript 0.2.426 rejects `const`; no list splice is required.

| Concern | lmaws | lmcloud / OpenTofu |
|---|---|---|
| State and recovery | Native private atomic state, per-step creation receipts and owned-resource rediscovery | Provider graph and private Terraform state |
| HTTP custom alias | Prepares ACM before initial distribution even for HTTP | HTTP fixture uses the CloudFront Host override; ACM optional |
| Weight shifts | One `web.step("dns_weighted", settings)` call, bounded INSYNC wait | Change two weights then apply provider graph |
| DNS sampling | lmcurl DoH with unique ECS /24 per sample, explicit resolve, three-sigma binomial band | Same DoH/resolve method, percentage tolerance |
| Initial name collision | Refused; first weighted write is CREATE | Provider detects conflicts during apply |
| Later drift | Owned targets must match before shift or delete | Refresh/plan exposes drift |
| Nano placement | Bounded subnet/type capacity fallback with distinct idempotency tokens | Provider launch and existing guarded teardown fallback |
| Cost | Durable price-table estimate; admitted HTTP upper bound retained on interruption | Documented price-table estimate |
| Lambda 03–06 | Live verified with lmaws only, custom logs and post-delivery audit | Live results recorded separately above |

Failure modes fixed while building the lmaws engine: standalone dynamic DNS no longer requires a certificate step; weighted steps are repeatable instead of being skipped as already complete; initial records cannot be adopted; all exact-name records are included in discovery, including foreign identifiers; teardown refuses foreign records. A local PATH executable older than v0.1.16 is rejected before provider dispatch. `scenarios/test-lmaws.sh` copies fixtures without private state to avoid replaying an already-destroyed run.


### lmaws measurements and script size

The corrected scenario 11 live run took **335.062 s up / 126.615 s test / 496.019 s down**. Load p95 was **221.47 ms**. Static/dynamic samples were **18/2**, **5/15**, **0/20**, respectively, with 20 samples at each target weight. The outward-rounded three-sigma binomial acceptance band permits the observed middle-step sample; zero static weight requires exactly zero static hits. Both attempt namespaces ended at zero active leftovers, verified by a separate lmaws process. See [numeric evidence](lmaws-results.json).

The successful run's conservative price-table estimate was **$0.00312048**; the complete two-attempt campaign was **$0.00601854**. These include admitted HTTP request/transfer bounds and are estimates, not bill measurements. The first attempt failed before sampling because a retry count exceeded lmcurl's limit of five. It was cleaned completely; the fixed driver uses bounded outer readiness rounds and records run/mode metadata per probe so fixture files cannot be mistaken for live evidence.

Physical `.lms` lines in each engine directory (including report scripts; inline statement density differs, so this is not a complexity score):

| Scenario | lmaws lines | lmcloud lines |
|---|---:|---:|
| 01 | 101 | 574 |
| 02 | 101 | 594 |
| 03 | 144 | 535 |
| 04 | 136 | 516 |
| 05 | 136 | 533 |
| 06 | 135 | 549 |
| 11 | 101 | 781 |

The lmaws engine additionally shares `scenarios/lib/lmaws.lms` (227 lines), root HTTP contracts and Python fixture adapters. The lmcloud engine shares `scenarios/lib/common.lms` and provider configuration. Static-only lmaws prepares ACM even for HTTP, so the live resource graphs differ from the no-ACM lmcloud HTTP variant; timings are not controlled benchmarks.


## Remaining lmaws scenarios

08, 09, 10 and 12 now have live lmaws evidence; 07 remains offline-only. No lmcloud live rerun was performed in this campaign, and the other engine's measurements above are preserved. Different wait strategies, payload paths and cost bounds prevent a performance ranking.

| Scenario | Up / test / down including settlement (s) | p95 (ms) | Conservative estimate | Leftovers |
|---|---:|---:|---:|---:|
| 08 | 24.0 / 21.3 / 619.6 | 427.8 | $0.00325006 | **0** |
| 09 | 26.6 / 11.2 / 619.5 | 391.8 | $0.00325006 | **0** |
| 10 | 585.2 / 19.4 / 637.5 | 131.8 | $0.00364746 | **0** |
| 12 | 323.3 / 208.3 / 432.0 | 142.8 | $0.00334755 | **0** |

| Friction | lmaws correction | Comparison boundary |
|---|---|---|
| Authenticated reads | Parse Function URL cookie arrays correctly, reject conflicting session cookies, strong DynamoDB read, Decimal serialization | Handler behavior, independent of deployment engine |
| Web bucket + Lambda signer | Accept exact run-bound site bucket and verify its actual run tag | Native ownership guard; OpenTofu resource references have a different naming boundary |
| Python upload configuration | Canonical integer environment values from the SDK JSON reader; import smoke before CloudFront | Native source assembly; no lmcloud change needed |
| DNS endpoint cutover | Wait 65 seconds after INSYNC for a 60-second TTL, retain counts before assertions, require all samples at endpoint weights | Recursive DNS caching affects either engine |
| Cleanup proof | Independent inventories plus late-log settlement; failed attempts retained | Empty receipts/state alone cannot exclude delayed runtime logs |
| Evidence isolation | Fixture copies and run-specific metric paths | Avoid mixing synthetic and live measurements in either engine |

All requests used lmaws/lmcurl scripting; no AWS CLI, admin profile or IAM edits. The maintenance probes use DoH and a CloudFront Host override, proving backend selection rather than browser TLS failover. Public images remain synthetic. The complete eight-attempt price-table estimate is $0.02382644; every namespace finished empty. See [RESULTS](RESULTS.md) and [numeric evidence](lmaws-remaining-results.json).

Relevant code: lmweblab `d096f8d` (safe lifecycle/cookies), `4f3b947` (fixture isolation), `9bf87ad` (DNS cache wait/import smoke); lmaws `d7bb7bd` (exact owned web bucket) and `bdb7cfd` (integer environment). A source build containing these host fixes is required until packaged in a release.

## Current lmaws Lambda engine comparison

| Scenario | Up / test / cleanup + checks (s) | Cold / warm HTTP (ms) | p95 (ms) | Conservative estimate | Leftovers |
|---|---:|---:|---:|---:|---:|
| 03 | 297.4 / 5.3 / 397.8 | 422.5 / 224.9 | 285.0 | $0.00348786 | **0** |
| 04 | 32.3 / 3.8 / 74.0 | 1142.2 / 234.0 | 1058.8 | $0.00315286 | **0** |
| 05 | 269.8 / 2.8 / 310.1 | 437.1 / 248.8 | 340.6 | $0.00349226 | **0** |
| 06 | 36.2 / 103.6 / 58.9 | 1480.4 / 297.5 | 1151.2 | $0.00378932 | **0** |

The existing lmcloud measurements above are the other coder's provider-backed runs. The engines use different wait/poll strategies and sampling points; timings are observations, not controlled performance rankings. Cost models also differ: the native ledger deliberately charges admitted worst-case Lambda/log/HTTP bounds, whereas the lmcloud table uses small fixed price-table estimates. Do not interpret that difference as a billing efficiency comparison.

| Issue | lmaws engine | lmcloud / OpenTofu engine |
|---|---|---|
| Execution role | Exact pre-created short name, STS account resolution and bounded Active waiter | Provider role ARN and Lambda lifecycle graph |
| Public Function URL | Both URL-only invoke permissions added by host | Two explicit permission resources required with the pinned provider |
| Logging | Pre-created/tagged custom group; create request includes LoggingConfig | Explicit aws_cloudwatch_log_group plus logging_config |
| Teardown after final log delivery | Private receipt, time window, absent-function check and bounded settlement; caught a group recreated minutes later | Provider graph/state is useful, but an immediate state-empty result alone cannot rule out late log delivery |
| Failure diagnostics | Private provider causes, phase exits, pre-assert load metrics and fresh inventory | Plan/apply/destroy diagnostics and provider waiters |
| Cold load boundary | One-second window failed a boto3 concurrency trial; five seconds completed all sixteen requests with no errors | Provider provisioning is separate from HTTP/load script duration |
| Scheduled reports | Only aws.events generates; HTTP reads do not increment; persisted counter and S3/DDB readback checked | See the committed lmcloud scenario implementation and measurements above |

Native changes landed in lmaws: custom logging, Active wait, URL deletion, independent serverless inventory, persistent cumulative caps and snapshots, receipt-scoped late-log reconciliation, and a 10-minute post-delivery settlement check. The policy builder now retains the exact Lambda-only PassRole statement from v6. No IAM policy, profile or role was changed by this campaign. LMScript 0.2.426 still uses uppercase let; no compiler change or list splice was needed. lmcurl required a caller-side load-window correction, not a host change.


## Scenario 07 SQS worker: live tests and cleanup recovery

The separately authorized run used only profile `lmaws` and the pre-created execution role under the Lead-reported v7b grant. The functional tests passed; the original `all` command returned **1** during cleanup. Teardown was repaired and independently verified empty across both attempts. No new functional run was started after the access denial.

| Up (s) | Test (s) | Initial down / recovery / final audit (s) | API root p95 (ms) | Selected attempt estimate | Full campaign estimate | Leftovers |
|---:|---:|---:|---:|---:|---:|---:|
| 78.192 | 101.772 | 47.932 / 623.014 / 15.471 | 458.594 | $0.01263188 | $0.01268908 | **0** |

The lmaws path made ownership and phase receipts explicit. The awkward parts were service JSON accidentally passing through display redaction, mapping readiness/deletion waiters, and tag-scoped IAM masking a missing-object Get. The client now proves exact-ARN absence with permitted list calls; it keeps the existing mutation ownership checks and never expands policy or retags mappings.

The original all-command failure is retained. Cleanup recovery is reported separately from provisioning/testing, so its duration includes log settlement but excludes the intervening diagnosis/build time; these are observations, not a deployment-engine benchmark. No lmcloud scenario 07 live rerun was performed here. Any Get-based waiter must account for this absence-authorization boundary; this campaign does not claim the other engine was affected.

Fix commits: lmweblab `f78d61d`; lmaws `3ce8fb5` (readiness, receipts, worker settlement), `5bb969b` (redrive wire data), `3b14634` (missing-object list proof). [Full evidence and limits](RESULTS.md#scenario-07-sqs-worker-live-tests-and-cleanup-recovery).
