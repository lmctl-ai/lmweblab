variable "run_id" {
  description = "Unique run identifier (4-16 lowercase alphanumeric chars) used for naming and lmaws_test tagging."
  type        = string
  default     = "demo01"

  validation {
    condition     = can(regex("^[a-z0-9]{4,16}$", var.run_id))
    error_message = "run_id must be 4 to 16 lowercase alphanumeric characters."
  }
}

variable "domain" {
  description = "Base Route 53 domain name (from LMWEBLAB_DOMAIN; committed default is example.com)."
  type        = string
  default     = "example.com"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]+\\.[a-z]{2,}\\.?$", var.domain))
    error_message = "domain must be a valid DNS domain name."
  }
}

variable "zone_id" {
  description = "Optional explicit Route 53 hosted zone ID; when empty in live mode, looked up by domain name."
  type        = string
  default     = ""
}

variable "aws_region" {
  description = "AWS region (must be us-east-1 per lmaws_session policy)."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.aws_region == "us-east-1"
    error_message = "aws_region must be us-east-1 per the lmaws_session policy."
  }
}

variable "aws_profile" {
  description = "AWS CLI/SDK profile name (must be lmaws for live runs)."
  type        = string
  default     = "lmaws"

  validation {
    condition     = contains(["lmaws", "default", ""], var.aws_profile)
    error_message = "aws_profile must be lmaws (or default/empty for offline validation)."
  }
}

variable "caller_cidr" {
  description = "Caller public IPv4 /32 CIDR allowed to reach TCP port 80 on the EC2 instance."
  type        = string
  default     = "203.0.113.10/32"

  validation {
    condition     = can(regex("^[0-9]{1,3}(\\.[0-9]{1,3}){3}/32$", var.caller_cidr)) && var.caller_cidr != "0.0.0.0/32"
    error_message = "caller_cidr must be a non-zero IPv4 /32 CIDR block."
  }
}

variable "instance_type" {
  description = "EC2 Spot nano instance type (only t4g.nano or t3.nano allowed by lmaws_session policy)."
  type        = string
  default     = "t4g.nano"

  validation {
    condition     = contains(["t4g.nano", "t3.nano"], var.instance_type)
    error_message = "instance_type must be t4g.nano or t3.nano."
  }
}

variable "ami_id" {
  description = "Optional explicit AMI ID; when empty in live mode, resolved via SSM public parameter for AL2023."
  type        = string
  default     = ""
}

variable "site_dir" {
  description = "Relative path to static site assets directory."
  type        = string
  default     = "../shared/site"
}

variable "user_data_path" {
  description = "Relative path to EC2 user-data script template."
  type        = string
  default     = "../shared/userdata/user_data.sh"
}

variable "enable_acm" {
  description = "Phase 2 toggle: request an ACM certificate in us-east-1 with Route 53 DNS validation and attach custom alias + HTTPS redirect on CloudFront."
  type        = bool
  default     = false
}

variable "offline_mode" {
  description = "When true, skips live AWS credential/metadata/data-source calls so tofu.plan runs completely offline."
  type        = bool
  default     = false
}
