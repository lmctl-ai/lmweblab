# Part A lmaws contract

The lmaws implementation is driven through `aws.example(...)` and keeps raw
provider identifiers in the private run state under `.lmweblab-local/`.

* `Cloud.web_stack(run_id, domain, state_path) -> Web` opens a persistent,
  run-owned session. `Web.step(operation, json_args) -> Row` supports the
  bucket, certificate, distribution/OAC, Route 53, compute, and HTTPS steps.
  `Web.status() -> Rows` returns masked state and timings; `Web.leftovers() -> Rows` queries provider state; `Web.down() -> Row`
  performs reverse teardown and proves zero leftovers.
* `Cloud.web_find(run_id, domain) -> Rows` is an independent read-only account
  inventory for the run prefix, tag, Route 53 names, CloudFront tags, and ACM
  names. `Cloud.leftovers` remains available for age-based read-only plans.

The native flow prepares ACM DNS validation before creating CloudFront because
the custom HTTP alias is accepted only when the distribution is created with a
certificate. It then tests HTTP, changes the viewer policy to HTTPS, and tests
again. Route 53 changes wait for INSYNC. CloudFront waits for bounded Deployed
state, and NotFound/visibility retries are bounded. Spot capacity retries are
bounded and only definite capacity or unsupported-AZ rejections are retried.

All mutations require `AWS_PROFILE=lmaws`, `LMAWS_LIVE=1`, us-east-1, the
`lmaws-site-`/`lmaws-app-` namespace, and `lmaws_test=<run_id>`. The security
group admits only the detected caller `/32`; the node is a tagged t3.nano or
t4g.nano with an 8 GiB encrypted gp3 root, bounded lifetime, and the committed
Python user-data server. The OAC nonce, DNS callbacks, HTTP admission record,
request/byte bounds, and lmcurl p95 result remain private or synthetic.

The contract is exercised by the offline demo transport and lmcurl fixtures;
the three levels are native lifecycle, HTTP contracts, and the actual Python
user-data handler on loopback. The tested host patch is v0.1.16. Live results are recorded separately as numeric summaries after independent cleanup verification.
