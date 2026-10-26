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
  clean_domain = trimsuffix(var.domain, ".")
  bucket_name  = "${var.name_prefix}-tf-${var.scenario_slug}-${var.run_id}"
  site_fqdn    = "${var.name_prefix}-tf-${var.scenario_slug}-site-${var.run_id}.${local.clean_domain}"

  common_tags = {
    lmaws_test = var.run_id
  }

  zone_id = var.zone_id != "" ? var.zone_id : (
    var.offline_mode ? "Z00000000000000000000" : data.aws_route53_zone.selected[0].zone_id
  )

  site_files = {
    "index.html" = {
      content_type  = "text/html; charset=utf-8"
      cache_control = "public, max-age=${var.html_cache_seconds}"
    }
    "about.html" = {
      content_type  = "text/html; charset=utf-8"
      cache_control = "public, max-age=${var.html_cache_seconds}"
    }
    "style.css" = {
      content_type  = "text/css; charset=utf-8"
      cache_control = "public, max-age=${var.asset_cache_seconds}"
    }
    "banner.png" = {
      content_type  = "image/png"
      cache_control = "public, max-age=${var.asset_cache_seconds}"
    }
    "404.html" = {
      content_type  = "text/html; charset=utf-8"
      cache_control = "no-cache"
    }
  }
}

data "aws_route53_zone" "selected" {
  count        = (!var.offline_mode && var.zone_id == "") ? 1 : 0
  name         = "${local.clean_domain}."
  private_zone = false
}

resource "aws_s3_bucket" "site" {
  bucket        = local.bucket_name
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = local.bucket_name
  })
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket = aws_s3_bucket.site.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "site_assets" {
  for_each = local.site_files

  bucket        = aws_s3_bucket.site.id
  key           = each.key
  source        = "${path.module}/${var.site_dir}/${each.key}"
  etag          = filemd5("${path.module}/${var.site_dir}/${each.key}")
  content_type  = each.value.content_type
  cache_control = each.value.cache_control

  tags = local.common_tags
}

resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${var.name_prefix}-tf-${var.scenario_slug}-oac-${var.run_id}"
  description                       = "OAC for ${local.bucket_name} (${var.run_id})"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_acm_certificate" "site" {
  count             = var.enable_acm ? 1 : 0
  domain_name       = local.site_fqdn
  validation_method = "DNS"

  tags = merge(local.common_tags, {
    Name = local.site_fqdn
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "site_cert_validation" {
  count           = var.enable_acm ? 1 : 0
  zone_id         = local.zone_id
  name            = tolist(aws_acm_certificate.site[0].domain_validation_options)[0].resource_record_name
  type            = tolist(aws_acm_certificate.site[0].domain_validation_options)[0].resource_record_type
  ttl             = 60
  records         = [tolist(aws_acm_certificate.site[0].domain_validation_options)[0].resource_record_value]
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "site" {
  count                   = var.enable_acm ? 1 : 0
  certificate_arn         = aws_acm_certificate.site[0].arn
  validation_record_fqdns = [aws_route53_record.site_cert_validation[0].fqdn]
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "lmweblab ${var.scenario_slug} ${var.run_id}"
  default_root_object = var.default_root_object
  price_class         = var.price_class
  wait_for_deployment = true
  aliases             = var.enable_acm ? [local.site_fqdn] : []

  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3-${local.bucket_name}"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-${local.bucket_name}"
    viewer_protocol_policy = var.enable_acm ? "redirect-to-https" : "allow-all"
    compress               = true
    min_ttl                = 0
    default_ttl            = var.html_cache_seconds
    max_ttl                = var.asset_cache_seconds

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }
  }

  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = var.error_page_path
    error_caching_min_ttl = 10
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = !var.enable_acm
    acm_certificate_arn            = var.enable_acm ? aws_acm_certificate_validation.site[0].certificate_arn : null
    ssl_support_method             = var.enable_acm ? "sni-only" : null
    minimum_protocol_version       = var.enable_acm ? "TLSv1.2_2021" : "TLSv1"
  }

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-tf-${var.scenario_slug}-cf-${var.run_id}"
  })
}

resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipalReadOnly"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.site.arn,
          "${aws_s3_bucket.site.arn}/*"
        ]
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.site.arn
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
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}
