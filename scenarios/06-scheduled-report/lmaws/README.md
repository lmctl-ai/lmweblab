![Scenario 06 architecture](images/s06_lmaws_architecture.png)

`lmctl all.lms`

![Scheduled run report](images/s06_lmaws_runs.png)
`lmctl test.lms`

The fake transport models an EventBridge `rate(1 minute)` rule invoking a bounded Lambda reporter that writes an HTML/JSON report to S3 and a run row to DynamoDB. The lmcurl test polls the report endpoint and checks its JSON shape. Live scheduling is held until the pre-created execution role is available.

Defaults: `us-east-1`, `lmaws-s06-*` names, 128 MiB/10 s, `$0.0000` offline and about `$0.0002` live. Run `lmctl up.lms`, `lmctl test.lms`, `lmctl down.lms`, or `lmctl all.lms`.
