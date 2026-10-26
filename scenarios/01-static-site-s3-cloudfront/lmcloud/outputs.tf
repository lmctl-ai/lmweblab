output "run_id" {
  value = var.run_id
}

output "domain" {
  value = local.clean_domain
}

output "bucket_name" {
  value = aws_s3_bucket.site.id
}

output "oac_id" {
  value = aws_cloudfront_origin_access_control.site.id
}

output "distribution_id" {
  value = aws_cloudfront_distribution.site.id
}

output "distribution_domain_name" {
  value = aws_cloudfront_distribution.site.domain_name
}

output "cloudfront_https_url" {
  value = "https://${aws_cloudfront_distribution.site.domain_name}"
}

output "site_fqdn" {
  value = local.site_fqdn
}

output "site_url" {
  value = var.enable_acm ? "https://${local.site_fqdn}" : "http://${local.site_fqdn}"
}
