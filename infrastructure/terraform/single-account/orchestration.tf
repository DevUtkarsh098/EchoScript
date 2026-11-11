data "archive_file" "dispatcher" {
  type        = "zip"
  source_dir  = "${path.module}/functions/dispatch"
  output_path = "${path.module}/build/dispatch.zip"
}

data "archive_file" "mark_failed" {
  type        = "zip"
  source_dir  = "${path.module}/functions/mark-failed"
  output_path = "${path.module}/build/mark-failed.zip"
}

data "archive_file" "acquire_slot" {
  type        = "zip"
  source_dir  = "${path.module}/functions/acquire-slot"
  output_path = "${path.module}/build/acquire-slot.zip"
}

data "archive_file" "release_slot" {
  type        = "zip"
  source_dir  = "${path.module}/functions/release-slot"
  output_path = "${path.module}/build/release-slot.zip"
}

resource "aws_cloudwatch_log_group" "dispatcher" {
  name              = "/aws/lambda/${local.name_prefix}-dispatch"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "mark_failed" {
  name              = "/aws/lambda/${local.name_prefix}-mark-failed"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "acquire_slot" {
  name              = "/aws/lambda/${local.name_prefix}-acquire-slot"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "release_slot" {
  name              = "/aws/lambda/${local.name_prefix}-release-slot"
  retention_in_days = 14
}

resource "aws_iam_role" "lambda_dispatcher" {
  name = "${local.name_prefix}-dispatcher"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "lambda_dispatcher" {
  name = "consume-queue-start-workflow-write-logs"
  role = aws_iam_role.lambda_dispatcher.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.jobs.arn
      },
      { Effect = "Allow", Action = ["states:StartExecution"], Resource = aws_sfn_state_machine.transcription.arn },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.dispatcher.arn}:*"
      }
    ]
  })
}

resource "aws_lambda_function" "dispatcher" {
  function_name    = "${local.name_prefix}-dispatch"
  role             = aws_iam_role.lambda_dispatcher.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.dispatcher.output_path
  source_code_hash = data.archive_file.dispatcher.output_base64sha256
  timeout          = 30
  memory_size      = 128
  environment {
    variables = { STATE_MACHINE_ARN = aws_sfn_state_machine.transcription.arn }
  }
  depends_on = [aws_iam_role_policy.lambda_dispatcher, aws_cloudwatch_log_group.dispatcher]
}

resource "aws_lambda_event_source_mapping" "jobs" {
  event_source_arn                   = aws_sqs_queue.jobs.arn
  function_name                      = aws_lambda_function.dispatcher.arn
  batch_size                         = 1
  function_response_types            = ["ReportBatchItemFailures"]
  enabled                            = true
  maximum_batching_window_in_seconds = 0
}

resource "aws_iam_role" "lambda_mark_failed" {
  name = "${local.name_prefix}-mark-failed"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "lambda_mark_failed" {
  name = "update-job-and-write-logs"
  role = aws_iam_role.lambda_mark_failed.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["dynamodb:UpdateItem"], Resource = aws_dynamodb_table.jobs.arn },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.mark_failed.arn}:*"
      }
    ]
  })
}

resource "aws_lambda_function" "mark_failed" {
  function_name    = "${local.name_prefix}-mark-failed"
  role             = aws_iam_role.lambda_mark_failed.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.mark_failed.output_path
  source_code_hash = data.archive_file.mark_failed.output_base64sha256
  timeout          = 15
  memory_size      = 128
  environment {
    variables = { DYNAMODB_TABLE = aws_dynamodb_table.jobs.name }
  }
  depends_on = [aws_iam_role_policy.lambda_mark_failed, aws_cloudwatch_log_group.mark_failed]
}

resource "aws_iam_role" "lambda_slots" {
  name = "${local.name_prefix}-worker-slots"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "lambda_slots" {
  name = "manage-worker-slot-leases"
  role = aws_iam_role.lambda_slots.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["dynamodb:UpdateItem"], Resource = aws_dynamodb_table.worker_slots.arn },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = ["${aws_cloudwatch_log_group.acquire_slot.arn}:*", "${aws_cloudwatch_log_group.release_slot.arn}:*"]
      }
    ]
  })
}

resource "aws_lambda_function" "acquire_slot" {
  function_name    = "${local.name_prefix}-acquire-slot"
  role             = aws_iam_role.lambda_slots.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.acquire_slot.output_path
  source_code_hash = data.archive_file.acquire_slot.output_base64sha256
  timeout          = 10
  memory_size      = 128
  environment {
    variables = {
      WORKER_SLOTS_TABLE = aws_dynamodb_table.worker_slots.name
      SLOT_LEASE_SECONDS = "43200"
    }
  }
  depends_on = [aws_iam_role_policy.lambda_slots, aws_cloudwatch_log_group.acquire_slot]
}

resource "aws_lambda_function" "release_slot" {
  function_name    = "${local.name_prefix}-release-slot"
  role             = aws_iam_role.lambda_slots.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.release_slot.output_path
  source_code_hash = data.archive_file.release_slot.output_base64sha256
  timeout          = 10
  memory_size      = 128
  environment {
    variables = { WORKER_SLOTS_TABLE = aws_dynamodb_table.worker_slots.name }
  }
  depends_on = [aws_iam_role_policy.lambda_slots, aws_cloudwatch_log_group.release_slot]
}

resource "aws_iam_role" "state_machine" {
  name = "${local.name_prefix}-workflow"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "states.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "state_machine" {
  name = "run-worker-and-mark-terminal-failures"
  role = aws_iam_role.state_machine.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ecs:RunTask"], Resource = aws_ecs_task_definition.worker.arn },
      { Effect = "Allow", Action = ["ecs:DescribeTasks", "ecs:StopTask", "ecs:ListTasks"], Resource = "*" },
      { Effect = "Allow", Action = ["events:PutRule", "events:PutTargets", "events:DescribeRule"], Resource = "*" },
      {
        Effect    = "Allow"
        Action    = ["iam:PassRole"]
        Resource  = [aws_iam_role.worker_execution.arn, aws_iam_role.worker_task.arn]
        Condition = { StringEquals = { "iam:PassedToService" = "ecs-tasks.amazonaws.com" } }
      },
      { Effect = "Allow", Action = ["lambda:InvokeFunction"], Resource = [aws_lambda_function.mark_failed.arn, aws_lambda_function.acquire_slot.arn, aws_lambda_function.release_slot.arn] }
    ]
  })
}

resource "aws_sfn_state_machine" "transcription" {
  name     = "${local.name_prefix}-transcription"
  role_arn = aws_iam_role.state_machine.arn
  type     = "STANDARD"
  definition = jsonencode({
    StartAt = "AcquireSlot"
    States = {
      AcquireSlot = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.acquire_slot.arn
          Payload      = { "job_id.$" = "$.job_id" }
        }
        ResultSelector = {
          "acquired.$" = "$.Payload.acquired"
          "slot_id.$"  = "$.Payload.slot_id"
        }
        ResultPath = "$.lease"
        Next       = "SlotAvailable"
      }
      SlotAvailable = {
        Type = "Choice"
        Choices = [{
          Variable      = "$.lease.acquired"
          BooleanEquals = true
          Next          = "RunTranscription"
        }]
        Default = "WaitForSlot"
      }
      WaitForSlot = { Type = "Wait", Seconds = 30, Next = "AcquireSlot" }
      RunTranscription = {
        Type           = "Task"
        Resource       = "arn:aws:states:::ecs:runTask.sync"
        TimeoutSeconds = 7200
        Parameters = {
          Cluster        = aws_ecs_cluster.workers.arn
          LaunchType     = "FARGATE"
          TaskDefinition = aws_ecs_task_definition.worker.arn
          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets        = aws_subnet.workers_public[*].id
              SecurityGroups = [aws_security_group.worker.id]
              AssignPublicIp = "ENABLED"
            }
          }
          Overrides = {
            ContainerOverrides = [{
              Name        = "transcribe-worker"
              "Command.$" = "States.Array('--job-id', $.job_id, '--user-sub', $.user_sub, '--language', $.language)"
            }]
          }
        }
        ResultPath = null
        Retry = [{
          ErrorEquals     = ["States.TaskFailed", "ECS.ServiceException", "ECS.AmazonECSException"]
          IntervalSeconds = 10
          BackoffRate     = 2
          MaxAttempts     = 2
        }]
        Catch = [{ ErrorEquals = ["States.ALL"], ResultPath = "$.failure", Next = "MarkFailed" }]
        Next  = "ReleaseSlot"
      }
      MarkFailed = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.mark_failed.arn
          Payload = {
            "job_id.$"   = "$.job_id"
            "user_sub.$" = "$.user_sub"
          }
        }
        ResultPath = "$.failure_update"
        Next       = "ReleaseAfterFailure"
      }
      ReleaseSlot = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.release_slot.arn
          Payload = {
            "job_id.$"  = "$.job_id"
            "slot_id.$" = "$.lease.slot_id"
          }
        }
        End = true
      }
      ReleaseAfterFailure = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.release_slot.arn
          Payload = {
            "job_id.$"  = "$.job_id"
            "slot_id.$" = "$.lease.slot_id"
          }
        }
        Next = "Failed"
      }
      Failed = { Type = "Fail", Error = "TranscriptionFailed", Cause = "Worker task failed after retries" }
    }
  })
  depends_on = [aws_iam_role_policy.state_machine]
}
