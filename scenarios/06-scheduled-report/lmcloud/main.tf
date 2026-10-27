provider "aws" {
  region                      = var.aws_region
  profile                     = var.offline_mode ? null : (var.aws_profile != "" ? var.aws_profile : null)
  access_key                  = var.offline_mode ? "mock_access_key" : null
  secret_key                  = var.offline_mode ? "mock_secret_key" : null
  skip_credentials_validation = var.offline_mode
  skip_metadata_api_check     = var.offline_mode
  skip_requesting_account_id  = var.offline_mode
  skip_region_validation      = var.offline_mode

  default_tags {
    tags = {
      lmaws_test = var.run_id
    }
  }
}

locals {
  bucket_name   = "${var.name_prefix}-tf-${var.scenario_slug}-${var.run_id}"
  table_name    = "${var.name_prefix}_tf_${var.scenario_slug}_runs_${var.run_id}"
  function_name = "${var.name_prefix}_tf_${var.scenario_slug}_${var.run_id}"
  log_group     = "${var.name_prefix}_tf_${var.scenario_slug}_logs_${var.run_id}"
  rule_name     = "${var.name_prefix}_tf_${var.scenario_slug}_rule_${var.run_id}"

  common_tags = {
    lmaws_test = var.run_id
  }

  account_id = var.offline_mode ? "000000000000" : data.aws_caller_identity.current[0].account_id
  role_arn   = "arn:aws:iam::${local.account_id}:role/${var.lambda_role_name}"
}

data "aws_caller_identity" "current" {
  count = var.offline_mode ? 0 : 1
}

data "archive_file" "fn_zip" {
  type        = "zip"
  source_file = "${path.module}/assets/reporter.py"
  output_path = "${path.module}/.lmweblab-local/reporter.zip"
}

resource "aws_s3_bucket" "reports" {
  bucket        = local.bucket_name
  force_destroy = true
  tags          = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "runs" {
  name         = local.table_name
  billing_mode = var.table_billing
  hash_key     = "run_seq"

  attribute {
    name = "run_seq"
    type = "N"
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "fn" {
  name              = local.log_group
  retention_in_days = 1
  tags              = local.common_tags
}

resource "aws_lambda_function" "reporter" {
  function_name    = local.function_name
  role             = local.role_arn
  handler          = "reporter.handler"
  runtime          = var.runtime
  memory_size      = var.memory_mb
  timeout          = var.timeout_s
  filename         = data.archive_file.fn_zip.output_path
  source_code_hash = data.archive_file.fn_zip.output_base64sha256

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.reports.id
      TABLE_NAME  = aws_dynamodb_table.runs.name
      RUN_ID      = var.run_id
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.fn.name
  }

  tags = local.common_tags
}

resource "aws_lambda_function_url" "reporter" {
  function_name      = aws_lambda_function.reporter.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "allow_public_invoke" {
  statement_id  = "FunctionURLAllowPublicInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reporter.function_name
  principal     = "*"
}

resource "aws_cloudwatch_event_rule" "every_minute" {
  name                = local.rule_name
  description         = "Trigger reporter Lambda every minute (${var.run_id})"
  schedule_expression = var.schedule_expression
  tags                = local.common_tags
}

resource "aws_cloudwatch_event_target" "reporter" {
  rule      = aws_cloudwatch_event_rule.every_minute.name
  target_id = "reporter-lambda"
  arn       = aws_lambda_function.reporter.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reporter.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_minute.arn
}
