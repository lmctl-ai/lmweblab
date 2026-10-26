variable "run_id" {
  type    = string
  default = "demo01"
}

variable "name_prefix" {
  type    = string
  default = "lmaws"
}

variable "scenario_slug" {
  type    = string
  default = "s03"
}

variable "domain" {
  type    = string
  default = "example.com"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_profile" {
  type    = string
  default = "lmaws"
}

variable "offline_mode" {
  type    = bool
  default = false
}

variable "lambda_role_name" {
  type    = string
  default = "lmaws_lambda_exec"
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "memory_mb" {
  type    = number
  default = 128
}

variable "timeout_s" {
  type    = number
  default = 10
}

variable "log_retention_days" {
  type    = number
  default = 1
}

variable "price_class" {
  type    = string
  default = "PriceClass_100"
}
