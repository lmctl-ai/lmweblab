![Scenario 06 architecture](images/s06_lmaws_architecture.png)

`lmctl all.lms`

![Scheduled run report](images/s06_lmaws_runs.png)
`lmctl test.lms`

The fake transport models an EventBridge `rate(1 minute)` rule invoking a bounded Lambda reporter that writes an HTML/JSON report to S3 and a run row to DynamoDB. The lmcurl test polls the report endpoint and checks its JSON shape. Live scheduling uses the pre-created execution role; only EventBridge events generate reports, while HTTP reads remain read-only.

Defaults: `us-east-1`, `lmaws-s06-*` names, 128 MiB/10 s, `$0.0000` offline and about `$0.0002` live. Run `lmctl up.lms`, `lmctl test.lms`, `lmctl down.lms`, or `lmctl all.lms`.


Live lifecycle (from this directory): set `AWS_PROFILE=lmaws`, `AWS_REGION=us-east-1`, a fresh hexadecimal `LMWEBLAB_RUN_ID`, and `LMWEBLAB_DOMAIN` for the authorized DNS zone. Run `lmctl all.lms --live`; use separate `up.lms`, `test.lms`, `status.lms`, `down.lms` commands when inspecting a phase. The driver attempts teardown on failure. All run state, logs, raw metrics and cost receipts stay under ignored `.lmweblab-local/`.

Every function sends logs to `lmaws_<slug>_logs_<run>`, created with the run tag and deleted during teardown. The default `/aws/lambda/` group is never used. Configured memory and timeout, admitted HTTP bounds, SDK requests and scheduled executions contribute to the conservative cost estimate. An action denial stops the scenario; no admin profile or permission-file edits are allowed. Final measured results are recorded in [../../RESULTS.md](../../RESULTS.md).
