output "run_id" {
  value = var.run_id
}

output "domain" {
  value = local.clean_domain
}

output "bucket_name" {
  value = aws_s3_bucket.site.id
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

output "split_fqdn" {
  value = local.split_fqdn
}

output "split_url" {
  value = "http://${local.split_fqdn}"
}

output "instance_id" {
  value = aws_instance.app.id
}

output "instance_public_ip" {
  value = aws_instance.app.public_ip
}

output "security_group_id" {
  value = aws_security_group.app.id
}

output "weight_static" {
  value = tostring(var.weight_static)
}

output "weight_dynamic" {
  value = tostring(var.weight_dynamic)
}
