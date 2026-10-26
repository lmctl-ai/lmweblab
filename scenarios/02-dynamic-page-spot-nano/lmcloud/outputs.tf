output "run_id" {
  value = var.run_id
}

output "domain" {
  value = local.clean_domain
}

output "app_fqdn" {
  value = local.app_fqdn
}

output "app_url" {
  value = "http://${local.app_fqdn}"
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
