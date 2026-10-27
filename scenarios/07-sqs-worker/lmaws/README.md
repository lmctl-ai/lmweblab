![Architecture](images/s07_lmaws_architecture.png) — `lmctl https://raw.githubusercontent.com/lmctl-ai/lmweblab/main/scenarios/07-sqs-worker/lmaws/report.lms`

![Queue report](images/s07_lmaws_queue.png) — `lmctl https://raw.githubusercontent.com/lmctl-ai/lmweblab/main/scenarios/07-sqs-worker/lmaws/report.lms`

Offline fake transport proves API enqueue, bounded worker completion, DynamoDB idempotency, and poison redrive to a DLQ after three receives. Running this example costs about `$0.0002` live, estimated from the local price table (prices vary by region).


All five lifecycle entry points have editable CONFIG values for region, domain, name prefix, slug, prebuilt execution role, runtime, API/worker source, memory, timeout, TTL and the `$0.05` cap. Uppercase `let` is used because the installed LMScript parser rejects `const`. Run `lmctl all.lms --offline`, or up/test/status/down separately. The offline lifecycle takes seconds; live provisioning and three visibility-timeout deliveries can take minutes.

Offline cost is **$0.0000**. All committed handler fixtures and pictures are synthetic. `all.lms` always attempts teardown; `down.lms` is repeatable and audits the simulated queues, mapping, functions/log groups and table independently. The execution role remains prebuilt; this scenario never creates IAM roles. Functions use custom `lmaws_<slug>_logs_<run>` groups.

Live validation awaits the Lead go and the event-source mapping grant in [IAM_REMAINING.md](../../IAM_REMAINING.md). The reviewed v6 function-only Lambda permission does not cover mapping ARNs or `CreateEventSourceMapping`. Live commands require `AWS_PROFILE=lmaws`, a fresh explicit `--run-id`, and `LMWEBLAB_REMAINING_LIVE_GO=1` set only after the Lead go. No real AWS calls were made in this work.
