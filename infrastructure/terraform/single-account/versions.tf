terraform {
  required_version = ">= 1.7"
  backend "s3" {}
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.23.0, < 7.0.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = ["598391748654"]
  default_tags {
    tags = {
      Project     = "echoscript"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" { state = "available" }

locals {
  name_prefix = "echoscript-${var.environment}"
  account_id  = data.aws_caller_identity.current.account_id
  common_env = {
    APP_ENV            = "production"
    MOCK_AUTH          = "false"
    MOCK_PROCESSING    = "false"
    MOCK_VIDEO         = "false"
    AWS_REGION         = var.region
    STORAGE_BACKEND    = "s3"
    REPOSITORY_BACKEND = "dynamodb"
    INPUT_BUCKET       = aws_s3_bucket.input.bucket
    OUTPUT_BUCKET      = aws_s3_bucket.output.bucket
    DYNAMODB_TABLE     = aws_dynamodb_table.jobs.name
    JOB_QUEUE_URL      = aws_sqs_queue.jobs.url
    COGNITO_ISSUER     = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.users.id}"
    COGNITO_CLIENT_ID  = aws_cognito_user_pool_client.web.id
    CORS_ORIGINS       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
  }
}
