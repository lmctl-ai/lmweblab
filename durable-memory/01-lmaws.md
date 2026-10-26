# Part A: lmaws implementation

The `lmaws/` driver opens a persistent `Cloud.web_stack(run, domain, state)`
session. Native `Web.step` performs the tagged S3, ACM, CloudFront/OAC, Route
53, and EC2 phases; `Web.status` returns masked state and timings; `Web.down`
tears down in reverse order and verifies zero owned leftovers. `Cloud.web_find`
is the independent read-only prefix/tag inventory. Raw IDs never enter public
reports.

The live profile is only `lmaws` in us-east-1. Site and app names use both the
`lmaws-site-` and `lmaws-app-` prefixes and every resource carries the exact
`lmaws_test` run tag. Native guards enforce caller `/32` ingress, nano-only
spot capacity, an 8 GiB encrypted gp3 root, bounded instance lifetime, and
tagged ownership. CloudFront, Route 53, ACM, and spot visibility waits are
bounded; definite unsupported-AZ or capacity rejections may be retried.

ACM DNS validation is prepared before CloudFront creation so the custom HTTP
alias is valid at creation. The first lmcurl phase records HTTP admission,
request and byte bounds, and p95 latency; the optional second phase enables
HTTPS and repeats the contracts. OAC nonces, DNS callbacks, and live summaries
stay in ignored private state. Committed pictures and timings are synthetic.

`test.sh`/`shared/tests/offline_gate.sh` cover the native lifecycle, static and
dynamic lmcurl contracts, bounded load p95, and the actual Python user-data
fixture on loopback. No AWS calls or real identifiers belong in this repository.
The lmaws host is currently a development/15-era patch build; no release or
final live result is recorded here.
