locals {
  account = "598391748654"
  region  = "us-west-2"
  nodes = merge({
    controller = { instance_type = "t3a.medium", disk_gb = 20 }
    validation = { instance_type = "t3a.large", disk_gb = 100 }
    release    = { instance_type = "t3a.large", disk_gb = 100 }
  }, var.enable_disposable_test_host ? { disposable = { instance_type = "t3a.large", disk_gb = 100 } } : {})
  deployment_roles = toset(["publish", "plan", "deploy", "frontend", "smoke"])
}

resource "terraform_data" "approval" {
  input = var.cost_approval_reference
  lifecycle {
    precondition {
      condition     = length(trimspace(var.cost_approval_reference)) >= 10
      error_message = "STOP: owner must approve the AWS hosting cost and access design before provisioning."
    }
    precondition {
      condition     = var.approved_account_budget_usd >= 220
      error_message = "STOP: obtain explicit owner approval for an account-wide monthly budget of at least $220."
    }
    precondition {
      condition     = toset(keys(var.application_role_policies)) == local.deployment_roles
      error_message = "Provide all five reviewed application IAM policies using confirmed existing resource/backend metadata."
    }
  }
}

data "aws_ami" "ubuntu" {
  owners = ["099720109477"]
  filter {
    name   = "image-id"
    values = [var.ubuntu_ami_id]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

resource "aws_vpc" "jenkins" {
  cidr_block           = "10.63.0.0/24"
  enable_dns_support   = true
  enable_dns_hostnames = true
  depends_on           = [terraform_data.approval]
}

resource "aws_subnet" "jenkins" {
  vpc_id                  = aws_vpc.jenkins.id
  cidr_block              = "10.63.0.0/25"
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = false
}

resource "aws_internet_gateway" "jenkins" { vpc_id = aws_vpc.jenkins.id }

resource "aws_route_table" "jenkins" {
  vpc_id = aws_vpc.jenkins.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.jenkins.id
  }
}

resource "aws_route_table_association" "jenkins" {
  subnet_id      = aws_subnet.jenkins.id
  route_table_id = aws_route_table.jenkins.id
}

resource "aws_security_group" "node" {
  for_each    = local.nodes
  name        = "echoscript-jenkins-${each.key}"
  description = "No public ingress or SSH; controller HTTPS only from CI agents"
  vpc_id      = aws_vpc.jenkins.id
  # Existing groups keep the inline TLS/DNS baseline while the agent HTTPS
  # rules are managed as dedicated resources below. Ignore inline egress
  # reconciliation so Terraform cannot remove either ownership set.
  lifecycle {
    ignore_changes = [egress]
  }
  egress {
    description = "TLS egress for SSM, registries and package repositories"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    description = "VPC DNS resolver for AWS and repository hostnames"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["10.63.0.2/32"]
  }
  egress {
    description = "VPC DNS resolver TCP fallback"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["10.63.0.2/32"]
  }
}

resource "aws_vpc_security_group_egress_rule" "agent_to_controller" {
  for_each = toset(["validation", "release"])

  security_group_id            = aws_security_group.node[each.key].id
  referenced_security_group_id = aws_security_group.node["controller"].id

  description = "Jenkins WebSocket HTTPS to controller"
  ip_protocol = "tcp"
  from_port   = 8443
  to_port     = 8443
}

resource "aws_vpc_security_group_ingress_rule" "agent_https" {
  for_each                     = toset(["validation", "release"])
  security_group_id            = aws_security_group.node["controller"].id
  referenced_security_group_id = aws_security_group.node[each.key].id
  from_port                    = 8443
  to_port                      = 8443
  ip_protocol                  = "tcp"
  description                  = "Agent WebSocket HTTPS on private addresses only"
}

resource "aws_cloudwatch_log_group" "jenkins" {
  name              = "/echoscript/jenkins"
  retention_in_days = 14
  depends_on        = [terraform_data.approval]
}

resource "aws_instance" "node" {
  for_each               = local.nodes
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = each.value.instance_type
  subnet_id              = aws_subnet.jenkins.id
  vpc_security_group_ids = [aws_security_group.node[each.key].id]
  # Public IPv4 is used only for outbound TLS; the security group has no public
  # ingress. This avoids a NAT gateway while keeping SSM and package access.
  associate_public_ip_address = false
  # AWS reports the historical association setting for these private hosts,
  # which would force replacement despite their having no public IPv4. Keep
  # existing instances and apply false when creating a new disposable host.
  lifecycle {
    ignore_changes = [associate_public_ip_address]
  }
  iam_instance_profile    = aws_iam_instance_profile.node[each.key].name
  disable_api_termination = each.key == "controller"
  monitoring              = false
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  credit_specification { cpu_credits = "standard" }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = each.value.disk_gb
    encrypted             = true
    delete_on_termination = each.key != "controller"
  }
  tags = {
    Name        = "echoscript-jenkins-${each.key}"
    JenkinsRole = each.key
  }
  depends_on = [aws_route_table_association.jenkins]
}

resource "aws_ec2_instance_state" "agent" {
  for_each    = toset(["validation", "release"])
  instance_id = aws_instance.node[each.key].id
  state       = var.agent_desired_state
}

resource "aws_ebs_volume" "controller" {
  availability_zone = var.availability_zone
  size              = 40
  type              = "gp3"
  encrypted         = true
  tags              = { Name = "echoscript-jenkins-data" }
  lifecycle { prevent_destroy = true }
  depends_on = [terraform_data.approval]
}

resource "aws_volume_attachment" "controller" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.controller.id
  instance_id = aws_instance.node["controller"].id
}
