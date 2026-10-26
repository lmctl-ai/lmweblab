output "run_id" {
  value = var.run_id
}

output "bucket_name" {
  value = aws_s3_bucket.reports.id
}

output "table_name" {
  value = aws_dynamodb_table.runs.name
}

output "function_name" {
  value = aws_lambda_function.reporter.function_name
}

output "function_url" {
  value = aws_lambda_function_url.reporter.function_url
}

output "rule_name" {
  value = aws_cloudwatch_event_rule.every_minute.name
}
