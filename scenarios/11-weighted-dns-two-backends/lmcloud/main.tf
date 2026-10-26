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
  split_fqdn   = "${var.name_prefix}-tf-split-${var.run_id}.${local.clean_domain}"
  app_fqdn     = "${var.name_prefix}-tf-${var.scenario_slug}-app-${var.run_id}.${local.clean_domain}"

  common_tags = {
    lmaws_test = var.run_id
  }

  ssm_ami_param = startswith(var.instance_type, "t4g.") ? "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64" : "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"

  zone_id = var.zone_id != "" ? var.zone_id : (
    var.offline_mode ? "Z00000000000000000000" : data.aws_route53_zone.selected[0].zone_id
  )

  ami_id = var.offline_mode ? "ami-0123456789abcdef0" : nonsensitive(data.aws_ssm_parameter.al2023_ami[0].value)

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

  user_data = replace(file("${path.module}/${var.user_data_path}"), "__RUN_ID__", var.run_id)
}

data "aws_route53_zone" "selected" {
  count        = (!var.offline_mode && var.zone_id == "") ? 1 : 0
  name         = "${local.clean_domain}."
  private_zone = false
}

data "aws_ssm_parameter" "al2023_ami" {
  count = !var.offline_mode ? 1 : 0
  name  = local.ssm_ami_param
}

# Backend A: Private S3 Bucket + CloudFront OAC Distribution
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

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "lmweblab ${var.scenario_slug} ${var.run_id}"
  default_root_object = "index.html"
  price_class         = var.price_class
  wait_for_deployment = true

  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3-${local.bucket_name}"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-${local.bucket_name}"
    viewer_protocol_policy = "allow-all"
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
    response_page_path    = "/404.html"
    error_caching_min_ttl = 10
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
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

# Backend B: EC2 Spot Nano Dynamic Server + /32 Security Group
resource "aws_security_group" "app" {
  name        = "${var.name_prefix}-tf-${var.scenario_slug}-sg-${var.run_id}"
  description = "Allow inbound TCP ${var.http_port} from caller /32 only (${var.run_id})"

  ingress {
    description = "HTTP from caller /32"
    from_port   = var.http_port
    to_port     = var.http_port
    protocol    = "tcp"
    cidr_blocks = [var.caller_cidr]
  }

  egress {
    description = "Allow outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-tf-${var.scenario_slug}-sg-${var.run_id}"
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
    volume_size           = var.volume_size_gb
    volume_type           = var.volume_type
    delete_on_termination = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-tf-${var.scenario_slug}-app-${var.run_id}"
  })

  volume_tags = merge(local.common_tags, {
    Name = "${var.name_prefix}-tf-${var.scenario_slug}-vol-${var.run_id}"
  })
}

# Shared Route 53 Weighted Records on lmaws-tf-split-<run_id>.<domain>
resource "aws_route53_record" "split_static" {
  zone_id         = local.zone_id
  name            = local.split_fqdn
  type            = "A"
  set_identifier  = "backend-a-static"
  allow_overwrite = true

  weighted_routing_policy {
    weight = var.weight_static
  }

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "split_dynamic" {
  zone_id         = local.zone_id
  name            = local.split_fqdn
  type            = "A"
  ttl             = var.dns_ttl
  set_identifier  = "backend-b-dynamic"
  allow_overwrite = true
  records         = [aws_instance.app.public_ip]

  weighted_routing_policy {
    weight = var.weight_dynamic
  }
}
