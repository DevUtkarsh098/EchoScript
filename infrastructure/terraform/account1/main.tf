terraform {
  required_version = ">= 1.7"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.80" } }
}
provider "aws" {
  region = var.region
  default_tags { tags = { Project = "echoscript", Environment = var.environment, Owner = "member-1" } }
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
variable "worker_instance_profile" { type = string }
variable "k3s_server_url" {
  type      = string
  sensitive = true
}
variable "k3s_token_ssm_parameter" { type = string }
module "network" {
  source               = "../modules/networking"
  name                 = "echoscript-account1"
  cidr                 = "10.10.0.0/16"
  availability_zones   = ["us-west-2a", "us-west-2b"]
  public_subnet_cidrs  = ["10.10.1.0/24", "10.10.2.0/24"]
  private_subnet_cidrs = ["10.10.11.0/24", "10.10.12.0/24"]
}
module "input" {
  source = "../modules/storage"
  name   = "${var.bucket_prefix}-input-${var.environment}"
}
module "output" {
  source = "../modules/storage"
  name   = "${var.bucket_prefix}-output-${var.environment}"
}
module "workers" {
  source                = "../modules/compute"
  name                  = "echoscript-whisper-workers"
  vpc_id                = module.network.vpc_id
  subnet_ids            = module.network.private_subnet_ids
  instance_profile_name = var.worker_instance_profile
  user_data = templatefile("${path.module}/worker-user-data.sh.tftpl", {
    server_url      = var.k3s_server_url
    token_parameter = var.k3s_token_ssm_parameter
    region          = var.region
  })
}
resource "aws_budgets_budget" "monthly" {
  name         = "echoscript-account1-monthly"
  budget_type  = "COST"
  limit_amount = "100"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
}

