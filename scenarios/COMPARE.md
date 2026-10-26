# lmweblab Part B (`lmcloud` / OpenTofu) — Comparison, Live Timings & Engineering Notes

## 1. Live Run Summary (Phase 1 HTTP vs Phase 2 ACM + HTTPS)

Both live runs executed end-to-end under the single least-privilege session profile **`AWS_PROFILE=lmaws`** in `us-east-1` with **no `aws` CLI** (`lmcloud`, `lmcurl`, and `lmaws` only), followed by complete teardown (`down.lms`) and independent `lmaws` zero-leftover verification.

| Phase / Metric | Phase 1 (`tfp1r2`, HTTP, 14 resources) | Phase 2 (`tfp2r2`, ACM + HTTPS, 17 resources) | Notes |
| --- | ---: | ---: | --- |
| Caller `/32` IP detection (`lmcurl`) | `181 ms` (`0.18 s`) | `242 ms` (`0.24 s`) | `https://checkip.amazonaws.com` |
| `tofu.fmt_check` + `tofu.init` + `tofu.validate` | `973 ms` (`0.97 s`) | `863 ms` (`0.86 s`) | Shared plugin cache + `.h1` hash sidecar (`lmcloud v0.1.11+`) |
| `tofu.plan` (live Route 53 + SSM lookups) | `3,506 ms` (`3.51 s`) | `3,978 ms` (`3.98 s`) | Phase 1: `14 to add`; Phase 2: `17 to add` |
| `tofu.apply` (incl. ACM DNS validation + CloudFront `Deployed`) | `227,870 ms` (`227.87 s`) | `269,429 ms` (`269.43 s`) | Phase 2 includes ACM cert issuance + DNS CNAME validation (`~41 s`) + CloudFront deploy |
| **Total `up.lms`** | **`232,350 ms` (`3m 52.4s`)** | **`274,272 ms` (`4m 34.3s`)** | |
| DNS + EC2 Spot boot readiness poll (`test.lms`) | `602 ms` (`0.60 s`) | `521 ms` (`0.52 s`) | Ready on first poll (`cloud-init` finished while CloudFront deployed) |
| Live `lmcurl` contract + 4-VU load suite | `3,066 ms` (`3.07 s`) | `3,907 ms` (`3.91 s`) | Phase 2 adds TLS cert chain + `301` HTTP->HTTPS redirect checks |
| **Total `test.lms`** (incl. `lmdraw` + `lmplot`) | **`3,828 ms` (`3.83 s`)** | **`4,529 ms` (`4.53 s`)** | |
| `tofu.destroy` (incl. CloudFront disable+delete + Spot fallback) | `276,161 ms` (`276.16 s`) | `314,800 ms` (`314.80 s`) | Verifies `tofu.state_list == ""` and post-destroy `tofu.plan` add count (`14` / `17`) |
| Independent `lmaws` leftover audit (`buckets`, `instances`, `sgs`) | `4,863 ms` (`4.86 s`) | `13,958 ms` (`13.96 s`) | **0 leftovers** in both runs |
| **Total `down.lms`** | **`281,026 ms` (`4m 41.0s`)** | **`328,762 ms` (`5m 28.8s`)** | **`leftovers_count: 0`** |
| **Estimated Run Cost** | **`$0.0040`** | **`$0.0040`** | Spot `t4g.nano` (~8 min) + 8 GiB `gp3` + public IPv4 + S3/CF/R53 requests |

---

## 2. Live HTTP / HTTPS Contract & Load Test Measurements (`lmcurl`)

| Metric | Phase 1 (`tfp1r2`, HTTP) | Phase 2 (`tfp2r2`, ACM + HTTPS) | Assertion Verified |
| --- | ---: | ---: | --- |
| CloudFront `GET /index.html` (`https://d....cloudfront.net`) | `165.57 ms` | `228.96 ms` | `200 OK`, body match, `Cache-Control: public, max-age=300` |
| CloudFront custom `404` (`GET /nonexistent-path-404.html`) | `352.92 ms` | `376.82 ms` | `404 Not Found`, custom `/404.html` body |
| Custom domain `https://lmaws-tf-site-<id>.<domain>` | N/A (Phase 1 tested via `http://` + `Host`) | `200 OK` (TLS verified) | X.509 certificate subject matches `lmaws-tf-site-<id>.<domain>`, valid chain, `301` redirect from `http://` |
| Dynamic EC2 Spot nano `GET /?echo=dns_ok` | `132.99 ms` | `218.06 ms` | `200 OK`, HTML-escaped query (`<script>alert(1)</script>` -> `&lt;script&gt;...`), `run_id` present |
| Dynamic `GET /api/info` JSON contract | PASS | PASS | JSON schema valid, `counter` strictly increases (`c2 > c1`), `time_ns` strictly increases (`ns2 > ns1`) |
| `curl.load` (4 virtual users, 20 requests to `/api/info`) p50 | `132.04 ms` | `129.23 ms` | `0.0%` error rate |
| `curl.load` p95 | `175.37 ms` | `177.81 ms` | `< 5000 ms` threshold PASS |
| `curl.load` p99 | `216.51 ms` | `180.14 ms` | |

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

### D. `lmscript` `${NAME}` Interpolation Note for Float Constants
- When a `CONFIG` constant holds an integer-valued float such as `let LOAD_DURATION_S = 2.0;` or `let P95_THRESHOLD_MS = 5000.0;`, JavaScript's number formatting emits `2` and `5000` (integer literals) when spliced via `${LOAD_DURATION_S}`, which triggers `_lmcode_: method Curl.load expects float for argument 3; found int`.
- **Workaround used**: Pass string constants `"2.0"` / `"5000.0"` with `str_to_float(${LOAD_DURATION_S})` inside `_dsl_` blocks (or non-integer float literals like `2.5`).

---

## 4. What Was Awkward in OpenTofu for This Stack

1. **Five-Resource Chain for a Single HTTPS Static Site**:
   - Attaching HTTPS to a CloudFront distribution in OpenTofu requires coordinating 5 separate resources across 3 AWS services (`aws_acm_certificate`, `aws_route53_record` for DNS validation, `aws_acm_certificate_validation` waiter, `aws_cloudfront_distribution`, and `aws_route53_record` alias), plus conditional `count = var.enable_acm ? 1 : 0` indexing on every reference.
2. **CloudFront Default Certificate vs `aliases` Exclusivity**:
   - CloudFront rejects `CreateDistributionWithTags` if `aliases` is non-empty while `cloudfront_default_certificate = true`. Phase 1 (HTTP) must set `aliases = []` on the distribution even when a Route 53 alias `A` record points to it, requiring callers in Phase 1 to either use the `d....cloudfront.net` hostname or set the `Host` header to `d....cloudfront.net`.
3. **`aws_instance` `root_block_device.tags` vs `provider.default_tags` / `volume_tags` Conflict**:
   - When `default_tags` is configured on `provider "aws"`, `terraform-provider-aws` automatically populates `volume_tags` on `aws_instance` and rejects `root_block_device { tags = ... }` at plan time with `"root_block_device.0.tags": conflicts with volume_tags`. Volume tags must be set via top-level `volume_tags` on `aws_instance`.
4. **CloudFront Edge Propagation Dominates Wall-Clock Time**:
   - Whereas S3, Route 53, Security Group, and EC2 Spot `t4g.nano` creation complete in ~35–45 seconds (and EC2 Spot `cloud-init` finishes booting Python's `http.server` in another ~15 seconds), `aws_cloudfront_distribution` `wait_for_deployment = true` takes ~3.5–4.5 minutes on create and ~4.5–5.2 minutes on disable+delete.
