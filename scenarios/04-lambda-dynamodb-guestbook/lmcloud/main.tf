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
  table_name    = "${var.name_prefix}_tf_${var.scenario_slug}_entries_${var.run_id}"
  function_name = "${var.name_prefix}_tf_${var.scenario_slug}_${var.run_id}"
  log_group     = "${var.name_prefix}_tf_${var.scenario_slug}_logs_${var.run_id}"

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
  source_file = "${path.module}/assets/guestbook.py"
  output_path = "${path.module}/.lmweblab-local/guestbook.zip"
}

resource "aws_dynamodb_table" "entries" {
  name         = local.table_name
  billing_mode = var.table_billing
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "fn" {
  name              = local.log_group
  retention_in_days = 1
  tags              = local.common_tags
}

resource "aws_lambda_function" "guestbook" {
  function_name    = local.function_name
  role             = local.role_arn
  handler          = "guestbook.handler"
  runtime          = var.runtime
  memory_size      = var.memory_mb
  timeout          = var.timeout_s
  filename         = data.archive_file.fn_zip.output_path
  source_code_hash = data.archive_file.fn_zip.output_base64sha256

  environment {
    variables = {
      TABLE_NAME  = aws_dynamodb_table.entries.name
      TTL_SECONDS = tostring(var.ttl_seconds)
      RUN_ID      = var.run_id
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.fn.name
  }

  tags = local.common_tags
}

resource "aws_lambda_function_url" "guestbook" {
  function_name      = aws_lambda_function.guestbook.function_name
  authorization_type = "NONE"
}
