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
  app_fqdn     = "${var.name_prefix}-tf-${var.scenario_slug}-app-${var.run_id}.${local.clean_domain}"
  sg_name      = "${var.name_prefix}-tf-${var.scenario_slug}-sg-${var.run_id}"
  app_name     = "${var.name_prefix}-tf-${var.scenario_slug}-app-${var.run_id}"
  vol_name     = "${var.name_prefix}-tf-${var.scenario_slug}-vol-${var.run_id}"

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

resource "aws_security_group" "app" {
  name        = local.sg_name
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
    Name = local.sg_name
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
    Name = local.app_name
  })

  volume_tags = merge(local.common_tags, {
    Name = local.vol_name
  })
}

resource "aws_route53_record" "app" {
  zone_id         = local.zone_id
  name            = local.app_fqdn
  type            = "A"
  ttl             = var.dns_ttl
  allow_overwrite = true
  records         = [aws_instance.app.public_ip]
}
