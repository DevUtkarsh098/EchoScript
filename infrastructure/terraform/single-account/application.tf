resource "aws_iam_role" "api_execution" {
  name = "${local.name_prefix}-api-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "api_execution" {
  role       = aws_iam_role.api_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "api_infrastructure" {
  name = "${local.name_prefix}-api-express-infrastructure"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "api_infrastructure" {
  role       = aws_iam_role.api_infrastructure.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices"
}

resource "aws_iam_role" "api_task" {
  name = "${local.name_prefix}-api-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "api_task" {
  name = "job-data-and-dispatch"
  role = aws_iam_role.api_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.input.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.output.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.jobs.arn
      },
      { Effect = "Allow", Action = ["sqs:SendMessage"], Resource = aws_sqs_queue.jobs.arn }
    ]
  })
}

resource "aws_ecs_express_gateway_service" "api" {
  service_name            = "${local.name_prefix}-api"
  cpu                     = "1024"
  memory                  = "2048"
  execution_role_arn      = aws_iam_role.api_execution.arn
  infrastructure_role_arn = aws_iam_role.api_infrastructure.arn
  task_role_arn           = aws_iam_role.api_task.arn
  health_check_path       = "/ready"

  primary_container {
    image          = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
    container_port = 8000

    aws_logs_configuration {
      log_group         = aws_cloudwatch_log_group.api.name
      log_stream_prefix = "api"
    }

    dynamic "environment" {
      for_each = merge(local.common_env, {
        MAX_UPLOAD_BYTES = tostring(var.max_upload_bytes)
        APP_VERSION      = "0.1.0"
        COMMIT_SHA       = var.image_tag
        DEPLOYMENT_COLOR = "single"
      })
      content {
        name  = environment.key
        value = environment.value
      }
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.api_execution,
    aws_iam_role_policy_attachment.api_infrastructure,
    aws_iam_role_policy.api_task,
  ]
}
