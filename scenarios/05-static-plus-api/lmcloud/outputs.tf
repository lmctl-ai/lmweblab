output "run_id" {
  value = var.run_id
}

output "bucket_name" {
  value = aws_s3_bucket.site.id
}

output "function_name" {
  value = aws_lambda_function.api.function_name
}

output "function_url" {
  value = aws_lambda_function_url.api.function_url
}

output "distribution_domain_name" {
  value = aws_cloudfront_distribution.unified.domain_name
}

output "site_fqdn" {
  value = local.site_fqdn
}
