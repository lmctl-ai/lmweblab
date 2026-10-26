variable "run_id" {
  description = "Short lowercase alphanumeric run identifier."
  type        = string
  default     = "demo01"

  validation {
    condition     = can(regex("^[a-z0-9]{4,16}$", var.run_id))
    error_message = "run_id must be 4-16 lowercase alphanumeric characters."
  }
}

variable "name_prefix" {
  description = "Resource naming prefix."
  type        = string
  default     = "lmaws"
}

variable "scenario_slug" {
  description = "Short scenario identifier included in resource names."
  type        = string
  default     = "s11"
}

variable "domain" {
  description = "Base Route 53 domain name."
  type        = string
  default     = "example.com"
}

variable "zone_id" {
  description = "Optional Route 53 Hosted Zone ID override."
  type        = string
  default     = ""
}

variable "aws_region" {
  description = "Target AWS region."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.aws_region == "us-east-1"
    error_message = "lmweblab scenarios are restricted to us-east-1."
  }
}

variable "aws_profile" {
  description = "AWS profile for live runs (lmaws only)."
  type        = string
  default     = "lmaws"

  validation {
    condition     = var.aws_profile == "lmaws" || var.aws_profile == ""
    error_message = "Only the single profile lmaws is permitted."
  }
}

variable "offline_mode" {
  description = "When true, skip live AWS data lookups and credential validation."
  type        = bool
  default     = false
}

variable "caller_cidr" {
  description = "Caller public IPv4 /32 CIDR allowed on TCP port 80."
  type        = string
  default     = "203.0.113.10/32"

  validation {
    condition     = can(regex("^[0-9]{1,3}(\\.[0-9]{1,3}){3}/32$", var.caller_cidr)) && var.caller_cidr != "0.0.0.0/32"
    error_message = "caller_cidr must be a non-zero /32 IPv4 CIDR."
  }
}

variable "instance_type" {
  description = "EC2 Spot nano instance type."
  type        = string
  default     = "t4g.nano"

  validation {
    condition     = contains(["t4g.nano", "t3.nano"], var.instance_type)
    error_message = "instance_type must be t4g.nano or t3.nano."
  }
}

variable "volume_size_gb" {
  description = "Root EBS volume size in GiB (<= 8)."
  type        = number
  default     = 8
}

variable "volume_type" {
  description = "Root EBS volume type."
  type        = string
  default     = "gp3"
}

variable "http_port" {
  description = "Inbound TCP port for dynamic HTTP server."
  type        = number
  default     = 80
}

variable "dns_ttl" {
  description = "Route 53 weighted A record TTL in seconds."
  type        = number
  default     = 60
}

variable "weight_static" {
  description = "Route 53 weighted routing weight (0..255) for Backend A (Static CloudFront)."
  type        = number
  default     = 90

  validation {
    condition     = var.weight_static >= 0 && var.weight_static <= 255
    error_message = "weight_static must be between 0 and 255."
  }
}

variable "weight_dynamic" {
  description = "Route 53 weighted routing weight (0..255) for Backend B (Dynamic EC2 Spot Nano)."
  type        = number
  default     = 10

  validation {
    condition     = var.weight_dynamic >= 0 && var.weight_dynamic <= 255
    error_message = "weight_dynamic must be between 0 and 255."
  }
}

variable "html_cache_seconds" {
  description = "Max-age cache seconds for HTML documents."
  type        = number
  default     = 300
}

variable "asset_cache_seconds" {
  description = "Max-age cache seconds for CSS and image assets."
  type        = number
  default     = 3600
}

variable "price_class" {
  description = "CloudFront price class."
  type        = string
  default     = "PriceClass_100"
}

variable "site_dir" {
  description = "Path to static site directory relative to module."
  type        = string
  default     = "../../../shared/site"
}

variable "user_data_path" {
  description = "Path to user_data script relative to module."
  type        = string
  default     = "../../../shared/userdata/user_data.sh"
}
