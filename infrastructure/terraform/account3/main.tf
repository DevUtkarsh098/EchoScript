terraform {
  required_version = ">= 1.7"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.80" } }
}
provider "aws" {
  region = var.region
  default_tags { tags = { Project = "echoscript", Environment = var.environment, Owner = "member-3" } }
}
variable "region" {
  type    = string
  default = "us-west-2"
}
variable "environment" {
  type    = string
  default = "demo"
}
variable "bucket_prefix" { type = string }
module "network" {
  source               = "../modules/networking"
  name                 = "echoscript-account3"
  cidr                 = "10.30.0.0/16"
  availability_zones   = ["us-west-2a", "us-west-2b"]
  public_subnet_cidrs  = ["10.30.1.0/24", "10.30.2.0/24"]
  private_subnet_cidrs = ["10.30.11.0/24", "10.30.12.0/24"]
}
module "video" {
  source = "../modules/storage"
  name   = "${var.bucket_prefix}-video-${var.environment}"
}
resource "aws_secretsmanager_secret" "heygen" {
  name                    = "echoscript/${var.environment}/heygen-api-key"
  recovery_window_in_days = 7
}
resource "aws_budgets_budget" "monthly" {
  name         = "echoscript-account3-monthly"
  budget_type  = "COST"
  limit_amount = "100"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
}
