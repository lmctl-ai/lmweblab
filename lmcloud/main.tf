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
  bucket_name  = "lmaws-tf-${var.run_id}"
  site_fqdn    = "lmaws-tf-site-${var.run_id}.${local.clean_domain}"
  app_fqdn     = "lmaws-tf-app-${var.run_id}.${local.clean_domain}"

  common_tags = {
    lmaws_test = var.run_id
  }

  ssm_ami_param = startswith(var.instance_type, "t4g.") ? "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64" : "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"

  zone_id = var.zone_id != "" ? var.zone_id : (
    var.offline_mode ? "Z00000000000000000000" : data.aws_route53_zone.selected[0].zone_id
  )

  ami_id = var.ami_id != "" ? var.ami_id : (
    var.offline_mode ? "ami-0123456789abcdef0" : nonsensitive(data.aws_ssm_parameter.al2023_ami[0].value)
  )

  site_files = {
    "index.html" = {
      content_type  = "text/html; charset=utf-8"
      cache_control = "public, max-age=300"
    }
    "about.html" = {
      content_type  = "text/html; charset=utf-8"
      cache_control = "public, max-age=300"
    }
    "style.css" = {
      content_type  = "text/css; charset=utf-8"
      cache_control = "public, max-age=3600"
    }
    "banner.png" = {
      content_type  = "image/png"
      cache_control = "public, max-age=3600"
    }
    "404.html" = {
      content_type  = "text/html; charset=utf-8"
      cache_control = "no-cache"
    }
  }

  user_data = replace(file("${path.module}/${var.user_data_path}"), "__RUN_ID__", var.run_id)
}

data "aws_route53_zone" "selected" {
  count        = (!var.offline_mode && var.zone_id == "") ? 1 : 0
  name         = "${local.clean_domain}."
  private_zone = false
}

data "aws_ssm_parameter" "al2023_ami" {
  count = (!var.offline_mode && var.ami_id == "") ? 1 : 0
  name  = local.ssm_ami_param
}

# 1. Private S3 bucket with Block Public Access enabled
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

# 2. CloudFront Origin Access Control (OAC) and distribution
resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "lmaws-tf-oac-${var.run_id}"
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
  comment             = "lmweblab ${var.run_id}"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
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
    default_ttl            = 300
    max_ttl                = 3600

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
    response_page_path    = "/404.html"
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
    Name = "lmaws-tf-cf-${var.run_id}"
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

# 3. Tagged EC2 security group (TCP 80 from caller /32 only) and Spot nano instance
resource "aws_security_group" "app" {
  name        = "lmaws-tf-sg-${var.run_id}"
  description = "Allow inbound TCP 80 from caller /32 only (${var.run_id})"

  ingress {
    description = "HTTP from caller /32"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.caller_cidr]
  }

  tags = merge(local.common_tags, {
    Name = "lmaws-tf-sg-${var.run_id}"
  })
}

resource "aws_instance" "app" {
  ami                         = local.ami_id
  instance_type               = var.instance_type
  vpc_security_group_ids      = [aws_security_group.app.id]
  associate_public_ip_address = true
  user_data                   = local.user_data
  user_data_replace_on_change = true

  instance_market_options {
    market_type = "spot"

    spot_options {
      spot_instance_type             = "one-time"
      instance_interruption_behavior = "terminate"
    }
  }

  root_block_device {
    volume_size           = 8
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = merge(local.common_tags, {
    Name = "lmaws-tf-app-${var.run_id}"
  })

  volume_tags = merge(local.common_tags, {
    Name = "lmaws-tf-vol-${var.run_id}"
  })
}

# 4. Route 53 records under lmaws-tf-site-<run_id>.<domain> and lmaws-tf-app-<run_id>.<domain>
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

resource "aws_route53_record" "app" {
  zone_id         = local.zone_id
  name            = local.app_fqdn
  type            = "A"
  ttl             = 60
  allow_overwrite = true
  records         = [aws_instance.app.public_ip]
}
