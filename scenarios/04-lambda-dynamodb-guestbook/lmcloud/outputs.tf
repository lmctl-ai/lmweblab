output "run_id" {
  value = var.run_id
}

output "table_name" {
  value = aws_dynamodb_table.entries.name
}

output "function_name" {
  value = aws_lambda_function.guestbook.function_name
}

output "function_url" {
  value = aws_lambda_function_url.guestbook.function_url
}
