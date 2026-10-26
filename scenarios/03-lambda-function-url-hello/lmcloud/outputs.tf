output "run_id" {
  value = var.run_id
}

output "function_name" {
  value = aws_lambda_function.api.function_name
}

output "function_url" {
  value = aws_lambda_function_url.api.function_url
}

output "distribution_domain_name" {
  value = aws_cloudfront_distribution.api.domain_name
}

output "api_fqdn" {
  value = local.api_fqdn
}
