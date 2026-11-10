variable "region" {
  type        = string
  description = "AWS region for the EchoScript deployment."
  default     = "us-west-2"
}

variable "environment" {
  type        = string
  description = "Short environment label used in resource names."
  default     = "prod"
  validation {
    condition     = can(regex("^[a-z0-9-]{2,10}$", var.environment))
    error_message = "environment must be 2-10 lowercase letters, digits, or hyphens."
  }
}

variable "image_tag" {
  type        = string
  description = "Immutable Git commit tag already pushed to both ECR repositories."
  validation {
    condition     = can(regex("^[a-f0-9]{7,40}$", var.image_tag))
    error_message = "image_tag must be an immutable hexadecimal Git commit tag."
  }
}

variable "monthly_budget_usd" {
  type        = number
  description = "AWS Budgets monthly cost limit in USD."
  default     = 100
}

variable "budget_alert_email" {
  type        = string
  description = "Optional address for AWS Budget threshold notifications."
  default     = ""
  validation {
    condition     = var.budget_alert_email == "" || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.budget_alert_email))
    error_message = "budget_alert_email must be blank or a valid email address."
  }
}

variable "max_upload_bytes" {
  type        = number
  description = "Maximum accepted audio object size."
  default     = 262144000
}
