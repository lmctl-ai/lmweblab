![Scenario 03 architecture](images/s03_lmaws_architecture.png)

`lmctl all.lms`

![Latency report](images/s03_lmaws_latency.png)
`lmctl test.lms`

Offline fake transport provisions a bounded Python Lambda (`python3.12`, 128 MiB, 10 seconds) with the pre-created `lmaws_lambda_exec` role and an explicitly justified public Function URL (`NONE` authentication). The lmcurl test checks JSON shape, cold/warm calls, and p95 latency. Live runs are enabled with the single `lmaws` profile and custom tagged logs.

| Config | Default |
| --- | --- |
| region | `us-east-1` |
| function prefix | `lmaws_` |
| role | `lmaws_lambda_exec` |
| cost | `$0.0000` offline; about `$0.0001` live |

Run each lifecycle command from this directory with `lmctl <file>.lms`; `down.lms` is safe to rerun and proves zero fake leftovers.


Live lifecycle (from this directory): set `AWS_PROFILE=lmaws`, `AWS_REGION=us-east-1`, a fresh hexadecimal `LMWEBLAB_RUN_ID`, and `LMWEBLAB_DOMAIN` for the authorized DNS zone. Run `lmctl all.lms --live`; use separate `up.lms`, `test.lms`, `status.lms`, `down.lms` commands when inspecting a phase. The driver attempts teardown on failure. All run state, logs, raw metrics and cost receipts stay under ignored `.lmweblab-local/`.

Every function sends logs to `lmaws_<slug>_logs_<run>`, created with the run tag and deleted during teardown. The default `/aws/lambda/` group is never used. Configured memory and timeout, admitted HTTP bounds, SDK requests and scheduled executions contribute to the conservative cost estimate. An action denial stops the scenario; no admin profile or permission-file edits are allowed. Final measured results are recorded in [../../RESULTS.md](../../RESULTS.md).
