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

locals {
  filename = "function.zip"
  file_hash = filesha256(local.filename)
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
  filename = local.filename
  function_name = "${var.infra_name_prefix}-bot"
  role = aws_iam_role.lambda_role.arn
  handler = "bot.callback_handler"
  source_code_hash = local.file_hash
  runtime = "python3.9"
  timeout = 10
  environment {
    variables = {
      BOT_ID = sensitive(var.bot_id)
      GOOGLE_SERVICE_ACCOUNT_CREDS = sensitive(base64decode(sensitive(var.google_service_account_creds)))
      GOOGLE_SHEET_ID = sensitive(var.google_sheet_id)
      GOOGLE_CALENDAR_ID = sensitive(var.google_calendar_id)
      API_CALLBACK_AUTH_TOKEN = sensitive(var.api_callback_auth_token)
    }
  }
}

resource "aws_lambda_function_url" "bot_url" {
  function_name      = aws_lambda_function.bot_lambda.function_name
  authorization_type = "NONE"
}


resource "aws_lambda_function" "daily_query_lambda" {
  filename = local.filename
  function_name = "${var.infra_name_prefix}-bot-daily"
  role = aws_iam_role.lambda_role.arn
  handler = "bot.daily_handler"
  source_code_hash = local.file_hash
  runtime = "python3.9"
  timeout = 10
  environment {
    variables = {
      BOT_ID = sensitive(var.bot_id)
      GOOGLE_SERVICE_ACCOUNT_CREDS = sensitive(base64decode(sensitive(var.google_service_account_creds)))
      GOOGLE_SHEET_ID = sensitive(var.google_sheet_id)
      API_CALLBACK_AUTH_TOKEN = sensitive(var.api_callback_auth_token)
    }
  }
}

resource "aws_lambda_function" "weekly_query_lambda" {
  filename = local.filename
  function_name = "${var.infra_name_prefix}-bot-weekly"
  role = aws_iam_role.lambda_role.arn
  handler = "bot.weekly_handler"
  source_code_hash = local.file_hash
  runtime = "python3.9"
  timeout = 10
  environment {
    variables = {
      BOT_ID = sensitive(var.bot_id)
      GOOGLE_SERVICE_ACCOUNT_CREDS = sensitive(base64decode(sensitive(var.google_service_account_creds)))
      GOOGLE_SHEET_ID = sensitive(var.google_sheet_id)
      API_CALLBACK_AUTH_TOKEN = sensitive(var.api_callback_auth_token)
    }
  }
}

resource "aws_cloudwatch_event_rule" "birthday_lambda_daily_event_rule" {
  name = "encounter-bot-birthday-lambda-event-rule"
  description = "Every day at 12PM UTC"
  schedule_expression = "cron(0 12 * * ? *)"
}

resource "aws_cloudwatch_event_target" "birthday_lambda_event_target" {
  arn = aws_lambda_function.daily_query_lambda.arn
  rule = aws_cloudwatch_event_rule.birthday_lambda_daily_event_rule.name
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_birthday_lambda" {
  statement_id = "AllowExecutionFromCloudWatch"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.daily_query_lambda.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.birthday_lambda_daily_event_rule.arn
}


resource "aws_cloudwatch_event_rule" "lambda_daily_event_rule" {
  name = "encounter-bot-birthday-daily-lambda-event-rule"
  description = "Every day at 12PM UTC except sunday"
  schedule_expression = "cron(0 0 12 ? * MON,TUE,WED,THU,FRI,SAT *)"
}


resource "aws_cloudwatch_event_target" "lambda_daily_event_target" {
  arn = aws_lambda_function.daily_query_lambda.arn
  rule = aws_cloudwatch_event_rule.lambda_daily_event_rule.name
}


resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda_daily" {
  statement_id = "AllowExecutionFromCloudWatch"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.daily_query_lambda.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.lambda_daily_event_rule.arn
}


resource "aws_cloudwatch_event_rule" "lambda_weekly_event_rule" {
  name = "encounter-bot-birthday-weekly-lambda-event-rule"
  description = "Every day at 12PM UTC only on sunday"
  schedule_expression = "cron(0 0 12 ? * SUN *)"
}

resource "aws_cloudwatch_event_target" "lambda_weekly_event_target" {
  arn = aws_lambda_function.weekly_query_lambda.arn
  rule = aws_cloudwatch_event_rule.lambda_weekly_event_rule.name
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda_weekly" {
  statement_id = "AllowExecutionFromCloudWatch"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.daily_query_lambda.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.lambda_weekly_event_rule.arn
}