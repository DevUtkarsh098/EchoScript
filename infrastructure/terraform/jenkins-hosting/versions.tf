terraform {
  required_version = ">= 1.7"
  backend "s3" {}
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.72.0"
    }
  }
}

provider "aws" {
  region              = "us-west-2"
  allowed_account_ids = ["598391748654"]
  default_tags {
    tags = {
      Project   = "echoscript-jenkins"
      ManagedBy = "terraform"
    }
  }
}
