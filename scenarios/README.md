# lmweblab Scenario Catalog

Self-contained AWS web deployment scenarios driven by LMScript (`lmctl <file>.lms`), comparing **`lmaws`** (Part A) and **`lmcloud` / OpenTofu** (Part B) under the single least-privilege session profile `AWS_PROFILE=lmaws`.

Every scenario directory (`scenarios/NN-name/`) is self-contained with editable `# === CONFIG ===` constants at the top of each `.lms` file spliced into `_dsl_` blocks via `${NAME}`.

## Catalog Index

| Directory | Pattern | AWS Services | Typical Live Cost | Typical Live Time (`up` / `test` / `down`) | What `test.lms` Proves |
| --- | --- | --- | ---: | ---: | --- |
| [`01-static-site-s3-cloudfront`](01-static-site-s3-cloudfront/lmcloud/README.md) | Private S3 static site fronted by CloudFront OAC + Route 53 alias (+ optional ACM HTTPS) | S3 (BPA + OAC policy), CloudFront (OAC SigV4, Gzip, custom 404), Route 53 Alias `A`, ACM (`--acm`) | `~$0.0005` (`$0.0000` offline) | `~228s`–`269s` / `~3.8s` / `~276s`–`315s` | 200 OK on `/index.html`, `/`, `/about.html`, `/style.css` (gzip), `/banner.png`, `Cache-Control` headers, custom `404` page, ACM TLS certificate subject/chain + `301` HTTP->HTTPS redirect (`--acm`), 0 leftovers |
| [`02-dynamic-page-spot-nano`](02-dynamic-page-spot-nano/lmcloud/README.md) | Dynamic Python 3 web server on one-time EC2 Spot `t4g.nano` + Route 53 `A` record | EC2 Spot `t4g.nano` (8 GiB `gp3`), Security Group (caller `/32` TCP 80 only), Route 53 `A`, SSM Parameter Store (AL2023 AMI) | `~$0.0035` (`$0.0000` offline) | `~35s` / `~3.1s` / `~45s` | HTML-escaped `?echo=` query rendering (`<script>` XSS prevention), monotonic `/api/info` request counter + nanosecond timestamp progression, JSON schema validation, 4-VU `curl.load` latency (`p95 < 5000 ms`), 0 leftovers |
| `03-lambda-function-url-hello` | Python Lambda + Function URL + CloudFront alias | Lambda, CloudFront, Route 53 | `~$0.0001` | Pending `lmaws_lambda_exec` role | JSON schema, cold vs warm latency |
| `04-lambda-dynamodb-guestbook` | Serverless guestbook API with TTL & pagination | Lambda Function URL, DynamoDB (PAY_PER_REQUEST) | `~$0.0002` | Pending `lmaws_lambda_exec` role | POST/GET entries, HTML escaping, pagination, TTL |
| `05-static-plus-api` | Single-domain S3 static site + `/api/*` Lambda origin | S3, CloudFront (2 origins), Lambda URL, Route 53 | `~$0.0005` | Pending `lmaws_lambda_exec` role | Same-origin `/` + `/api/*` routing without CORS, per-path caching |
| `06-scheduled-report` | Every-minute EventBridge scheduled Lambda writer | EventBridge, Lambda, S3, DynamoDB | `~$0.0002` | Pending `lmaws_lambda_exec` role | N scheduled executions observed in S3 + DynamoDB |
| `07-sqs-worker` | Async API enqueue + SQS worker + DLQ | Lambda, SQS (+ DLQ), DynamoDB | `~$0.0002` | Pending `lmaws_lambda_exec` role | Async completion + poison message routed to DLQ |
| `08-session-login-demo` | Cookie session auth backed by DynamoDB TTL | Lambda URL, DynamoDB | `~$0.0002` | Pending `lmaws_lambda_exec` role | Login -> authenticated session cookie -> logout -> expiry |
| `09-url-shortener` | Short-code redirect service with hit counters | Lambda URL, DynamoDB | `~$0.0002` | Pending `lmaws_lambda_exec` role | `301`/`302` redirect, `404` unknown code, atomic hit counter |
| `10-presigned-upload-gallery` | Presigned S3 `PUT` uploads + CloudFront delivery | Lambda URL, S3, CloudFront | `~$0.0005` | Pending `lmaws_lambda_exec` role | Presigned upload, CloudFront fetch, content-type & size bounds |
| `11-blue-green-weighted-dns` | Route 53 weighted traffic shift (`90/10` -> `0/100`) | Route 53 weighted records + endpoints | `~$0.0010` | Planned | Observed traffic distribution across weighted shift |
| `12-maintenance-page-failover` | Route 53 cutover between dynamic app and S3 maintenance site | Route 53, S3/CloudFront, EC2/Lambda | `~$0.0040` | Planned | Live traffic cutover to static maintenance page and back |

## Shared Libraries & Reports

- [`scenarios/lib/common.lms`](lib/common.lms): Shared helpers for CLI/env flags, `run_id` lifecycle, caller `/32` IP detection via `lmcurl`, and independent zero-leftover verification via `lmaws`.
- [`scenarios/COMPARE.md`](COMPARE.md): Engineering comparison, OpenTofu friction notes, and `lmcloud` / `lmscript` improvements (`lmcloud v0.1.11` and `v0.1.12`).
- [`scenarios/RESULTS.md`](RESULTS.md): Sanitized live run timings, latency measurements, cost estimates, and zero-leftover proofs.
