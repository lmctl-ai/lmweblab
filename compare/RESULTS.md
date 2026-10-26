# Web stack results

Part A was verified live with the single `lmaws` profile in us-east-1. The public report contains only numeric results; identifiers, URLs and raw receipts remain private. Part B is maintained separately in [the lmcloud implementation](../lmcloud/README.md).

| Part A phase | Seconds | Result |
|---|---:|---|
| Private S3 assets | 6.22 | Passed |
| ACM request and DNS validation | 33.02 | Passed |
| Initial CloudFront deployment with certificate | 157.30 | Passed |
| Site alias propagation | 25.82 | Passed |
| Tagged spot nano creation/readiness | 9.68 | Passed |
| App DNS propagation | 24.10 | Passed |
| HTTP contracts and load | 7.25 | 22 requests; load p95 390.70 ms |
| HTTPS viewer-policy deployment | 73.88 | Passed |
| HTTPS contracts and load | 4.80 | 22 requests; load p95 151.88 ms |
| Reverse teardown and provider checks | 406.58 | Passed |

Both the CloudFront name and the custom alias served the static site. Checks covered exact 404s, CSS/image types, caching headers, actual gzip encoding, HTML escaping, JSON schema, run identity, increasing counters/timestamps and response time. A separate lmcurl request confirmed HTTP 301 with an HTTPS location.

The successful stack estimate, including that redirect check, was **$0.00107766**. All attempts and independent provider checks were estimated at **$0.00513459**. Estimates use the request price table, transfer bounds, nano bid ceiling, public IPv4 and 8 GiB gp3 time; prices vary by region and free-tier credits are not deducted. Early receipt formats use a conservative storage bound.

A fresh native lmaws process queried seven attempt namespaces using provider inventories and found **zero active leftovers**. Terminated-instance and closed one-time Spot request history is retained by AWS and is excluded from active leftovers. See [the sanitized evidence](../evidence/lmaws-summary.json).

## Tool differences and improvements

Part A uses explicit lmscript lifecycle steps and a durable native creation ledger. Its cleanup requires current run tags, exact DNS scope and the private OAC creation proof. Part B uses OpenTofu state; its timings and parity results should be compared after its own independently verified run, rather than inferred from Part A.

The integration added guarded S3/CloudFront/Route 53/ACM/EC2 web APIs to lmaws, bounded placement and visibility retries, HTTP cost admission, and independent provider verification. Certificate preparation precedes initial CloudFront creation because custom HTTP aliases also require a covering certificate. A compiler environment-propagation fix was independently reviewed; explicit process settings keep the driver compatible with already-released CLI versions. lmcurl required no host change; its existing assertions, captures, schema validation, retries and load APIs perform the checks.
