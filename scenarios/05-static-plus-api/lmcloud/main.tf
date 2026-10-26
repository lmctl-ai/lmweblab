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
  bucket_name   = "${var.name_prefix}-tf-${var.scenario_slug}-${var.run_id}"
  function_name = "${var.name_prefix}_tf_${var.scenario_slug}_${var.run_id}"
  log_group     = "${var.name_prefix}_tf_${var.scenario_slug}_logs_${var.run_id}"
  site_fqdn     = "${var.name_prefix}-tf-${var.scenario_slug}-site-${var.run_id}.${local.clean_domain}"

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
  source_file = "${path.module}/assets/api.py"
  output_path = "${path.module}/.lmweblab-local/api.zip"
}

resource "aws_s3_bucket" "site" {
  bucket        = local.bucket_name
  force_destroy = true
  tags          = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "index" {
  bucket        = aws_s3_bucket.site.id
  key           = "index.html"
  source        = "${path.module}/${var.site_dir}/index.html"
  etag          = filemd5("${path.module}/${var.site_dir}/index.html")
  content_type  = "text/html; charset=utf-8"
  cache_control = "public, max-age=${var.html_cache_seconds}"
  tags          = local.common_tags
}

resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${var.name_prefix}-tf-${var.scenario_slug}-oac-${var.run_id}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudwatch_log_group" "fn" {
  name              = local.log_group
  retention_in_days = 1
  tags              = local.common_tags
}

resource "aws_lambda_function" "api" {
  function_name    = local.function_name
  role             = local.role_arn
  handler          = "api.handler"
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

resource "aws_cloudfront_distribution" "unified" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3-${local.bucket_name}"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

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
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-${local.bucket_name}"
    viewer_protocol_policy = "allow-all"
    compress               = true
    min_ttl                = 0
    default_ttl            = var.html_cache_seconds
    max_ttl                = 3600

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  ordered_cache_behavior {
    path_pattern           = "/api/*"
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

resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipalReadOnly"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = ["s3:GetObject", "s3:ListBucket"]
        Resource  = [aws_s3_bucket.site.arn, "${aws_s3_bucket.site.arn}/*"]
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.unified.arn
          }
        }
      }
    ]
  })
  depends_on = [aws_s3_bucket_public_access_block.site]
}

resource "aws_route53_record" "site_alias" {
  zone_id         = local.zone_id
  name            = local.site_fqdn
  type            = "A"
  allow_overwrite = true

  alias {
    name                   = aws_cloudfront_distribution.unified.domain_name
    zone_id                = aws_cloudfront_distribution.unified.hosted_zone_id
    evaluate_target_health = false
  }
}
