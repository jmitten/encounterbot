terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "4.52.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.4.3"
    }
  }
  required_version = ">= 1.1.0"
}

provider "aws" {
  region = var.region
  access_key = var.aws_access_key_id
  secret_key = var.aws_secret_access_key
}

resource "aws_iam_role" "lambda_role" {
  name_prefix = "${var.infra_name_prefix}_lambda_role_${var.region}"
  assume_role_policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Action = "sts:AssumeRole"
          Principal = {
            Service = "lambda.amazonaws.com"
          },
          Effect = "Allow"
        }
      ]
    })
}

resource "aws_iam_role_policy" "lambda_role_policy" {
  role = aws_iam_role.lambda_role.id
  name_prefix = "${var.infra_name_prefix}_lambda_policy_${var.region}"
  policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Action = [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ],
          Resource = "*"
        }
      ]
    })
}

resource "aws_lambda_function" "bot_lambda" {
  filename = "function.zip"
  function_name = var.infra_name_prefix
  role = aws_iam_role.lambda_role.arn
  handler = "bot.callback_handler"
  source_code_hash = filesha256("function.zip")
  runtime = "python3.9"
  timeout = 10
}