![Scenario 05 architecture](images/s05_lmaws_architecture.png)

`lmctl all.lms`

![Latency report](images/s05_lmaws_latency.png)
`lmctl test.lms`

This fake-transport scenario models one CloudFront hostname with `/` served from a private S3 bucket and `/api/*` sent to a Lambda Function URL. lmcurl asserts both JSON and static responses, cache-safe API behavior, and a bounded p95. Function URL `NONE` authentication is explicit and limited to this test fixture.

Defaults are `us-east-1`, `lmaws-s05-*` names, 128 MiB/10 s, `$0.0000` offline and about `$0.0005` live. Use `lmctl up.lms`, `lmctl test.lms`, `lmctl down.lms`, or `lmctl all.lms`.


Live lifecycle (from this directory): set `AWS_PROFILE=lmaws`, `AWS_REGION=us-east-1`, a fresh hexadecimal `LMWEBLAB_RUN_ID`, and `LMWEBLAB_DOMAIN` for the authorized DNS zone. Run `lmctl all.lms --live`; use separate `up.lms`, `test.lms`, `status.lms`, `down.lms` commands when inspecting a phase. The driver attempts teardown on failure. All run state, logs, raw metrics and cost receipts stay under ignored `.lmweblab-local/`.

Every function sends logs to `lmaws_<slug>_logs_<run>`, created with the run tag and deleted during teardown. The default `/aws/lambda/` group is never used. Configured memory and timeout, admitted HTTP bounds, SDK requests and scheduled executions contribute to the conservative cost estimate. An action denial stops the scenario; no admin profile or permission-file edits are allowed. Final measured results are recorded in [../../RESULTS.md](../../RESULTS.md).
