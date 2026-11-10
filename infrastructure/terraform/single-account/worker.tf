resource "aws_vpc" "workers" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_internet_gateway" "workers" {
  vpc_id = aws_vpc.workers.id
}

resource "aws_subnet" "workers_public" {
  count                   = 2
  vpc_id                  = aws_vpc.workers.id
  cidr_block              = "10.42.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false
}

resource "aws_route_table" "workers_public" {
  vpc_id = aws_vpc.workers.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.workers.id
  }
}

resource "aws_route_table_association" "workers_public" {
  count          = 2
  subnet_id      = aws_subnet.workers_public[count.index].id
  route_table_id = aws_route_table.workers_public.id
}

resource "aws_security_group" "worker" {
  name        = "${local.name_prefix}-worker"
  description = "Fargate worker has outbound HTTPS only and no inbound access"
  vpc_id      = aws_vpc.workers.id

  egress {
    description = "AWS APIs and model download endpoints"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_cluster" "workers" {
  name = "${local.name_prefix}-workers"
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${local.name_prefix}-transcribe-worker"
  retention_in_days = 14
}

resource "aws_iam_role" "worker_execution" {
  name = "${local.name_prefix}-worker-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "worker_execution" {
  name = "pull-worker-image-and-write-logs"
  role = aws_iam_role.worker_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
        Resource = aws_ecr_repository.worker.arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.worker.arn}:*"
      }
    ]
  })
}

resource "aws_iam_role" "worker_task" {
  name = "${local.name_prefix}-worker-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "worker_task" {
  name = "read-audio-write-transcripts"
  role = aws_iam_role.worker_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.input.arn}/*" },
      { Effect = "Allow", Action = ["s3:PutObject"], Resource = "${aws_s3_bucket.output.arn}/*" },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.jobs.arn
      }
    ]
  })
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name_prefix}-transcribe-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "2048"
  memory                   = "6144"
  execution_role_arn       = aws_iam_role.worker_execution.arn
  task_role_arn            = aws_iam_role.worker_task.arn

  container_definitions = jsonencode([{
    name      = "transcribe-worker"
    image     = "${aws_ecr_repository.worker.repository_url}:${var.image_tag}"
    essential = true
    environment = [
      { name = "AWS_REGION", value = var.region },
      { name = "INPUT_BUCKET", value = aws_s3_bucket.input.bucket },
      { name = "OUTPUT_BUCKET", value = aws_s3_bucket.output.bucket },
      { name = "DYNAMODB_TABLE", value = aws_dynamodb_table.jobs.name },
      { name = "WHISPER_MODEL", value = "tiny" },
      { name = "WHISPER_COMPUTE_TYPE", value = "int8" },
      { name = "WHISPER_CACHE_DIR", value = "/models" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.worker.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "task"
      }
    }
  }])

  depends_on = [aws_iam_role_policy.worker_execution]
}
