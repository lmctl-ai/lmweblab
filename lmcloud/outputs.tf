output "run_id" {
  description = "Active run identifier used for resource names and lmaws_test tags."
  value       = var.run_id
}

output "tag_key" {
  description = "Mandatory tag key applied to all resources."
  value       = "lmaws_test"
}

output "tag_value" {
  description = "Mandatory tag value applied to all resources."
  value       = var.run_id
}

output "domain" {
  description = "Base DNS domain."
  value       = local.clean_domain
}

output "zone_id" {
  description = "Route 53 hosted zone ID."
  value       = local.zone_id
}

output "bucket_name" {
  description = "Private S3 bucket name for the static site."
  value       = aws_s3_bucket.site.id
}

output "bucket_arn" {
  description = "Private S3 bucket ARN."
  value       = aws_s3_bucket.site.arn
}

output "oac_id" {
  description = "CloudFront Origin Access Control ID."
  value       = aws_cloudfront_origin_access_control.site.id
}

output "distribution_id" {
  description = "CloudFront distribution ID."
  value       = aws_cloudfront_distribution.site.id
}

output "distribution_domain_name" {
  description = "CloudFront default domain name (d....cloudfront.net)."
  value       = aws_cloudfront_distribution.site.domain_name
}

output "cloudfront_http_url" {
  description = "HTTP URL on the CloudFront distribution domain."
  value       = "http://${aws_cloudfront_distribution.site.domain_name}"
}

output "cloudfront_https_url" {
  description = "HTTPS URL on the CloudFront distribution domain."
  value       = "https://${aws_cloudfront_distribution.site.domain_name}"
}

output "site_fqdn" {
  description = "Route 53 site record FQDN."
  value       = local.site_fqdn
}

output "site_url" {
  description = "Primary site URL."
  value       = var.enable_acm ? "https://${local.site_fqdn}" : "http://${local.site_fqdn}"
}

output "app_fqdn" {
  description = "Route 53 dynamic app record FQDN."
  value       = local.app_fqdn
}

output "app_url" {
  description = "Dynamic EC2 app HTTP URL."
  value       = "http://${local.app_fqdn}"
}

output "instance_id" {
  description = "EC2 Spot nano instance ID."
  value       = aws_instance.app.id
}

output "instance_public_ip" {
  description = "EC2 Spot nano instance public IPv4."
  value       = aws_instance.app.public_ip
}

output "security_group_id" {
  description = "EC2 security group ID."
  value       = aws_security_group.app.id
}

output "caller_cidr" {
  description = "Authorized caller /32 CIDR."
  value       = var.caller_cidr
}
