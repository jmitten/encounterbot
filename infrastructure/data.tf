data "aws_caller_identity" "current" {}

data "archive_file" "lambdas" {
  output_path = "lambda.zip"
  type = "zip"
  source_dir = "${path.module}/../src"
}