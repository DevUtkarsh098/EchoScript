terraform {
  required_version = ">= 1.7"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.80" } }
}
provider "aws" {
  region = var.region
  default_tags { tags = { Project = "echoscript", Environment = var.environment, Owner = "member-2" } }
}
variable "region" {
  type    = string
  default = "us-west-2"
}
variable "environment" {
  type    = string
  default = "demo"
}
module "network" {
  source               = "../modules/networking"
  name                 = "echoscript-account2"
  cidr                 = "10.20.0.0/16"
  availability_zones   = ["us-west-2a", "us-west-2b"]
  public_subnet_cidrs  = ["10.20.1.0/24", "10.20.2.0/24"]
  private_subnet_cidrs = ["10.20.11.0/24", "10.20.12.0/24"]
}
resource "aws_ecr_repository" "images" {
  for_each = toset(["gateway-ui", "ingest-service", "transcribe-worker", "video-service"])
  name     = "echoscript/${each.key}"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}
resource "aws_budgets_budget" "monthly" {
  name         = "echoscript-account2-monthly"
  budget_type  = "COST"
  limit_amount = "125"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
}

