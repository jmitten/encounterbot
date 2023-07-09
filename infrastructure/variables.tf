variable "region" {
  default = "us-east-2"
}
variable "aws_access_key_id" {
  type        = string
  sensitive   = true
}

variable "aws_secret_access_key" {
  type        = string
  sensitive   = true
}

variable "infra_name_prefix" {
  type = string
}

variable "bot_id" {
  type = string
  sensitive = true
}

variable "google_sheet_id" {
  type = string
  sensitive = true
}

variable "google_service_account_creds" {
  type = string
  sensitive = true
}

variable "api_callback_auth_token" {
  type = string
  sensitive = true
}