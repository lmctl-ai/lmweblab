![Scenario 04 architecture](images/s04_lmaws_architecture.png)

`lmctl all.lms`

![Latency report](images/s04_lmaws_latency.png)
`lmctl test.lms`

Offline fake transport checks a public, explicitly justified Function URL backed by a tagged on-demand DynamoDB table with TTL and cursor-friendly access. The lmcurl test covers POST/GET, bounded pagination, JSON shape and escaping. Live execution uses the pre-created `lmaws_lambda_exec` role and never edits it.

Defaults: `us-east-1`, names `lmaws_s04_*`, 128 MiB/10 s, TTL 3600 s, `$0.0000` offline and about `$0.0002` live. Run `lmctl up.lms`, `lmctl test.lms`, `lmctl down.lms` from this directory.


Live lifecycle (from this directory): set `AWS_PROFILE=lmaws`, `AWS_REGION=us-east-1`, a fresh hexadecimal `LMWEBLAB_RUN_ID`, and `LMWEBLAB_DOMAIN` for the authorized DNS zone. Run `lmctl all.lms --live`; use separate `up.lms`, `test.lms`, `status.lms`, `down.lms` commands when inspecting a phase. The driver attempts teardown on failure. All run state, logs, raw metrics and cost receipts stay under ignored `.lmweblab-local/`.

Every function sends logs to `lmaws_<slug>_logs_<run>`, created with the run tag and deleted during teardown. The default `/aws/lambda/` group is never used. Configured memory and timeout, admitted HTTP bounds, SDK requests and scheduled executions contribute to the conservative cost estimate. An action denial stops the scenario; no admin profile or permission-file edits are allowed. Final measured results are recorded in [../../RESULTS.md](../../RESULTS.md).
