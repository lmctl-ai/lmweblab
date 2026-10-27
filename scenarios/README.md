# lmweblab Scenario Catalog

Self-contained AWS web deployment scenarios driven by LMScript (`lmctl <file>.lms`), comparing **`lmaws`** (Part A) and **`lmcloud` / OpenTofu** (Part B) under the single least-privilege session profile `AWS_PROFILE=lmaws`.

Every scenario directory (`scenarios/NN-name/`) is self-contained with editable `# === CONFIG ===` constants at the top of each `.lms` file spliced into `_dsl_` blocks via `${NAME}`.

## Catalog Index

| Directory | Pattern | AWS Services | Typical Live Cost | Typical Time (`up` / `test` / `down`) | What `test.lms` Proves |
| --- | --- | --- | ---: | ---: | --- |
| [`01-static-site-s3-cloudfront`](01-static-site-s3-cloudfront/lmcloud/README.md) | Private S3 static site fronted by CloudFront OAC + Route 53 alias (+ optional ACM HTTPS) | S3 (BPA + OAC policy), CloudFront (OAC SigV4, Gzip, custom 404), Route 53 Alias `A`, ACM (`--acm`) | `~$0.0005` (`$0.0000` offline) | `~228s`–`269s` / `~3.8s` / `~276s`–`315s` | 200 OK on `/index.html`, `/`, `/about.html`, `/style.css` (gzip), `/banner.png`, `Cache-Control` headers, custom `404` page, ACM TLS certificate subject/chain + `301` HTTP->HTTPS redirect (`--acm`), 0 leftovers |
| [`02-dynamic-page-spot-nano`](02-dynamic-page-spot-nano/lmcloud/README.md) | Dynamic Python 3 web server on one-time EC2 Spot `t4g.nano` + Route 53 `A` record | EC2 Spot `t4g.nano` (8 GiB `gp3`), Security Group (caller `/32` TCP 80 only), Route 53 `A`, SSM Parameter Store (AL2023 AMI) | `~$0.0035` (`$0.0000` offline) | `~35s` / `~3.1s` / `~45s` | HTML-escaped `?echo=` query rendering (`<script>` XSS prevention), monotonic `/api/info` request counter + nanosecond timestamp progression, JSON schema validation, 4-VU `curl.load` latency (`p95 < 5000 ms`), 0 leftovers |
| [`03-lambda-function-url-hello`](03-lambda-function-url-hello/lmcloud/README.md) | Python Lambda + Function URL + CloudFront alias | Lambda (`python3.12`), CloudWatch Logs (`lmaws_*`), CloudFront, Route 53 | `~$0.0001` (`$0.0000` offline) | Offline `all.lms`: `~9s` (Live pending `lmaws_lambda_exec`) | JSON schema validation, cold vs warm invocation latency, 4-VU load (`p95 < 2000 ms`) |
| [`04-lambda-dynamodb-guestbook`](04-lambda-dynamodb-guestbook/lmcloud/README.md) | Serverless guestbook API with TTL & pagination | Lambda Function URL, DynamoDB (`PAY_PER_REQUEST`, TTL), CloudWatch Logs | `~$0.0002` (`$0.0000` offline) | Offline `all.lms`: `~8s` (Live pending `lmaws_lambda_exec`) | `POST`/`GET` entries, HTML escaping (`<script>` XSS check), cursor pagination, TTL attribute |
| [`05-static-plus-api`](05-static-plus-api/lmcloud/README.md) | Single-domain S3 static site + `/api/*` Lambda origin | S3 (OAC), CloudFront (2 origins: `/` -> S3, `/api/*` -> Lambda URL), Lambda URL, Route 53 | `~$0.0005` (`$0.0000` offline) | Offline `all.lms`: `~9s` (Live pending `lmaws_lambda_exec`) | Same-origin `/` + `/api/*` routing without CORS, static cache hit vs dynamic `TTL=0` |
| [`06-scheduled-report`](06-scheduled-report/lmcloud/README.md) | Every-minute EventBridge scheduled Lambda writer | EventBridge (`rate(1 minute)`), Lambda, S3, DynamoDB, CloudWatch Logs | `~$0.0002` (`$0.0000` offline) | Offline `all.lms`: `~9s` (Live pending `lmaws_lambda_exec`) | Manual trigger + scheduled EventBridge executions recorded in S3 + DynamoDB |
| `07-sqs-worker` | Async API enqueue + SQS worker + DLQ | Lambda, SQS (+ DLQ), DynamoDB | `~$0.0002` | Pending `lmaws_lambda_exec` role | Async completion + poison message routed to DLQ |
| `08-session-login-demo` | Cookie session auth backed by DynamoDB TTL | Lambda URL, DynamoDB | `~$0.0002` | Pending `lmaws_lambda_exec` role | Login -> authenticated session cookie -> logout -> expiry |
| `09-url-shortener` | Short-code redirect service with hit counters | Lambda URL, DynamoDB | `~$0.0002` | Pending `lmaws_lambda_exec` role | `301`/`302` redirect, `404` unknown code, atomic hit counter |
| `10-presigned-upload-gallery` | Presigned S3 `PUT` uploads + CloudFront delivery | Lambda URL, S3, CloudFront | `~$0.0005` | Pending `lmaws_lambda_exec` role | Presigned upload, CloudFront fetch, content-type & size bounds |
| [`11-weighted-dns-two-backends`](11-weighted-dns-two-backends/lmcloud/README.md) | Route 53 weighted traffic shift (`90/10` -> `50/50` -> `0/100`) across static CloudFront + dynamic EC2 Spot nano | Route 53 weighted `A` records (`backend-a-static` & `backend-b-dynamic`), S3 + CloudFront OAC, EC2 Spot `t4g.nano` + `/32` SG | `~$0.0040` (`$0.0000` offline) | Live (`s11r01`): `502.3s` / `107.1s` / `284.7s` (Offline: `10.0s`) | Observed traffic share across `90/10` (`85%/15%`), `50/50` (`35%/65%`), and `0/100` (`0%/100%`) within binomial confidence bands (`N=20`/step), 0 leftovers + DNS `NXDOMAIN` post-destroy |
| `12-maintenance-page-failover` | Route 53 cutover between dynamic app and S3 maintenance site | Route 53, S3/CloudFront, EC2/Lambda | `~$0.0040` | Planned | Live traffic cutover to static maintenance page and back |

## Shared Libraries & Reports

- [`scenarios/lib/common.lms`](lib/common.lms): Shared helpers for CLI/env flags, `run_id` lifecycle, caller `/32` IP detection via `lmcurl`, and independent zero-leftover verification via `lmaws`.
- [`scenarios/COMPARE.md`](COMPARE.md): Engineering comparison, OpenTofu friction notes, IAM action matrix for Lambda Scenarios 03–06, and `lmcloud` / `lmscript` improvements (`lmcloud v0.1.11` and `v0.1.12`).
- [`scenarios/RESULTS.md`](RESULTS.md): Sanitized live run timings, latency and traffic-split measurements, cost estimates, and zero-leftover proofs.


## lmaws engine

The [`lmaws/` implementations](../lmaws/README.md) also have independent scenario directories:

- [01 static site](01-static-site-s3-cloudfront/lmaws/README.md)
- [02 dynamic nano](02-dynamic-page-spot-nano/lmaws/README.md)
- [03 Lambda hello](03-lambda-function-url-hello/lmaws/README.md), [04 guestbook](04-lambda-dynamodb-guestbook/lmaws/README.md), [05 static + API](05-static-plus-api/lmaws/README.md), [06 scheduled report](06-scheduled-report/lmaws/README.md): offline only pending authorization.
- [11 weighted DNS](11-weighted-dns-two-backends/lmaws/README.md)

Run each from its engine directory: `lmctl all.lms --offline`. Live commands require `AWS_PROFILE=lmaws` and an authorized `LMWEBLAB_DOMAIN`; every run keeps its own ignored state. New weighted/Lambda APIs require the current lmaws source build on PATH until a release includes them. The original combined-stack entry points remain available.
