![Scenario 05 architecture](images/s05_lmaws_architecture.png)

`lmctl all.lms --offline`

# Static S3 site plus Lambda API: lmaws engine

Live verified using **AWS_PROFILE=lmaws** only. Use a current source-built lmaws containing custom logging and `Serverless.settle`; older release binaries may predate these additions. Run from this directory.

```sh
# Set AWS_PROFILE=lmaws, AWS_REGION=us-east-1 and a fresh hexadecimal LMWEBLAB_RUN_ID.
# Set LMWEBLAB_DOMAIN for scenarios 03 and 05 to the authorized zone.
lmctl all.lms --live
# Inspect individual phases when needed:
lmctl status.lms --live
lmctl down.lms --live
# Offline pictures and handler contracts:
lmctl all.lms --offline
```

All five entry points start with editable CONFIG settings: region/domain, slug, runtime/handler/source, memory, timeout, TTL, schedule, HTTP timeout, load count/window, p95 limit and cost cap. Defaults are python3.12, 128 MiB, 10 seconds, sixteen load requests over at most five seconds, and a $0.05 component cap. The paired web budget remains below the run ceiling. Names and the pre-created role are constrained to the lmaws sandbox.

Measured up/test/cleanup plus checks: **269.8 / 2.8 / 310.1 seconds**. First cold/warm HTTP: **437.1 / 248.8 ms**; load p95 **340.6 ms**. Running this example costs about **$0.00349226** under the conservative admitted-bound model; offline charge $0.00. See [results and recovery details](../../RESULTS.md).

Functions use `lmaws_<slug>_logs_<run>`, created/tagged before deployment and deleted after the function. The default log group is never used. AWS log delivery may be delayed; down includes bounded post-delivery settlement, which can add up to ten minutes when run immediately. Exact private creation receipts restrict any late empty-tag repair. Raw state, endpoints, logs, metrics and cost ledgers remain in ignored `.lmweblab-local/`. The role and IAM policy are never modified.

![Latency report](images/s05_lmaws_latency.png)

`lmctl all.lms --offline`

Committed pictures use synthetic fixtures. Final provider-backed audit found **zero leftovers** after the delivery window.
