# lmweblab Live Run Results

All live runs below were executed using **`AWS_PROFILE=lmaws`** only in `us-east-1`, with zero `aws` CLI usage (`lmcloud`, `lmcurl`, and `lmaws` only), and verified to leave **0 resources** behind. Sensitive account IDs, hosted zone IDs, distribution IDs, instance IDs, and caller IPs are omitted from committed files.

## Part B (`lmcloud` / OpenTofu v1.13.2, `lmcloud v0.1.12`)

### 1. Full Stack Live Runs (`lmcloud/`)

| Run ID | Phase | Resources | `up.lms` Total (`init` / `plan` / `apply`) | `test.lms` Total (Wait / Suite) | `curl.load` Latency (p50 / p95 / p99) | `down.lms` Total (`destroy` / `audit`) | Leftovers (`tofu` + `lmaws`) | Est. Cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `tfp1r2` | Phase 1 (HTTP: S3 + OAC + CloudFront + Route 53 Alias + EC2 Spot `t4g.nano`) | 14 | `232.35 s` (`0.97 s` / `3.51 s` / `227.87 s`) | `3.83 s` (`0.60 s` / `3.07 s`) | `132.04 ms` / `175.37 ms` / `216.51 ms` | `281.03 s` (`276.16 s` / `4.86 s`) | **`0`** (`state_list=""`, `buckets=0`, `instances=0`, `sgs=0`) | `$0.0040` |
| `tfp2r2` | Phase 2 (ACM + HTTPS: adds ACM cert + Route 53 DNS validation CNAME + `redirect-to-https` custom alias) | 17 | `274.27 s` (`0.86 s` / `3.98 s` / `269.43 s`) | `4.53 s` (`0.52 s` / `3.91 s`) | `129.23 ms` / `177.81 ms` / `180.14 ms` | `328.76 s` (`314.80 s` / `13.96 s`) | **`0`** (`state_list=""`, post-destroy `plan add=17`, `buckets=0`, `instances=0`, `sgs=0`) | `$0.0040` |

### 2. Re-Homed Scenario Runs (`scenarios/`)

| Scenario | Engine | Offline `all.lms` Time | Planned Resources | Live Evidence | Est. Cost |
| --- | --- | ---: | ---: | --- | ---: |
| [`01-static-site-s3-cloudfront`](01-static-site-s3-cloudfront/lmcloud/README.md) | `lmcloud` | `8.87 s` | 11 (HTTP) / 14 (ACM) | Proven in `tfp1r2` (HTTP) and `tfp2r2` (ACM + HTTPS), 0 leftovers | `$0.0005` live / `$0.0000` offline |
| [`02-dynamic-page-spot-nano`](02-dynamic-page-spot-nano/lmcloud/README.md) | `lmcloud` | `7.13 s` | 3 (SG + Spot `t4g.nano` + Route 53 `A`) | Proven in `tfp1r2` and `tfp2r2` (`p50 ~130 ms`, `p95 ~176 ms`), 0 leftovers | `$0.0035` live / `$0.0000` offline |
