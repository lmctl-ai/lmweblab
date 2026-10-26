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
  default     = "s01"
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

variable "enable_acm" {
  description = "When true, provision an ACM TLS certificate and enable HTTPS on the custom alias."
  type        = bool
  default     = false
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

variable "default_root_object" {
  description = "CloudFront default root object."
  type        = string
  default     = "index.html"
}

variable "error_page_path" {
  description = "CloudFront 404 custom error page path."
  type        = string
  default     = "/404.html"
}

variable "site_dir" {
  description = "Path to static site directory relative to module."
  type        = string
  default     = "../../../shared/site"
}
