# Scenario 04: Lambda Function URL + DynamoDB Guestbook (`lmcloud`)

![Scenario 04 Architecture](images/s04_lmcloud_architecture.png)

`lmctl scenarios/04-lambda-dynamodb-guestbook/lmcloud/all.lms`

![Scenario 04 Latency](images/s04_lmcloud_latency.png)

`lmctl scenarios/04-lambda-dynamodb-guestbook/lmcloud/test.lms`

## Overview

Deploys a serverless guestbook with `aws_dynamodb_table` (`lmaws_tf_s04_entries_<run_id>`, `PAY_PER_REQUEST`, TTL on `expires_at`), `aws_cloudwatch_log_group`, `aws_lambda_function` (`lmaws_tf_s04_<run_id>`), and `aws_lambda_function_url`.
