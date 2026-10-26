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
  clean_domain  = trimsuffix(var.domain, ".")
  function_name = "${var.name_prefix}_tf_${var.scenario_slug}_${var.run_id}"
  log_group     = "${var.name_prefix}_tf_${var.scenario_slug}_logs_${var.run_id}"
  api_fqdn      = "${var.name_prefix}-tf-${var.scenario_slug}-api-${var.run_id}.${local.clean_domain}"

  common_tags = {
    lmaws_test = var.run_id
  }

  account_id = var.offline_mode ? "000000000000" : data.aws_caller_identity.current[0].account_id
  role_arn   = "arn:aws:iam::${local.account_id}:role/${var.lambda_role_name}"
  zone_id    = var.offline_mode ? "Z00000000000000000000" : data.aws_route53_zone.selected[0].zone_id

  fn_url_domain = replace(replace(aws_lambda_function_url.api.function_url, "https://", ""), "/", "")
}

data "aws_caller_identity" "current" {
  count = var.offline_mode ? 0 : 1
}

data "aws_route53_zone" "selected" {
  count        = var.offline_mode ? 0 : 1
  name         = "${local.clean_domain}."
  private_zone = false
}

data "archive_file" "fn_zip" {
  type        = "zip"
  source_file = "${path.module}/assets/handler.py"
  output_path = "${path.module}/.lmweblab-local/handler.zip"
}

resource "aws_cloudwatch_log_group" "fn" {
  name              = local.log_group
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_lambda_function" "api" {
  function_name    = local.function_name
  role             = local.role_arn
  handler          = "handler.handler"
  runtime          = var.runtime
  memory_size      = var.memory_mb
  timeout          = var.timeout_s
  filename         = data.archive_file.fn_zip.output_path
  source_code_hash = data.archive_file.fn_zip.output_base64sha256

  environment {
    variables = {
      RUN_ID = var.run_id
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.fn.name
  }

  tags = local.common_tags
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
}

resource "aws_cloudfront_distribution" "api" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "lmweblab ${var.scenario_slug} ${var.run_id}"
  price_class     = var.price_class

  origin {
    domain_name = local.fn_url_domain
    origin_id   = "lambda-${local.function_name}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "lambda-${local.function_name}"
    viewer_protocol_policy = "allow-all"
    compress               = true
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0

    forwarded_values {
      query_string = true

      cookies {
        forward = "none"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = local.common_tags
}

resource "aws_route53_record" "api_alias" {
  zone_id         = local.zone_id
  name            = local.api_fqdn
  type            = "A"
  allow_overwrite = true

  alias {
    name                   = aws_cloudfront_distribution.api.domain_name
    zone_id                = aws_cloudfront_distribution.api.hosted_zone_id
    evaluate_target_health = false
  }
}
