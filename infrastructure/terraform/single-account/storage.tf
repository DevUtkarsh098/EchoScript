resource "aws_s3_bucket" "input" {
  bucket = "echoscript-${local.account_id}-${var.environment}-input"
}

resource "aws_s3_bucket" "output" {
  bucket = "echoscript-${local.account_id}-${var.environment}-output"
}

resource "aws_s3_bucket" "frontend" {
  bucket = "echoscript-${local.account_id}-${var.environment}-web"
}

resource "aws_s3_bucket_public_access_block" "data" {
  for_each                = { input = aws_s3_bucket.input.id, output = aws_s3_bucket.output.id, frontend = aws_s3_bucket.frontend.id }
  bucket                  = each.value
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "data" {
  for_each = { input = aws_s3_bucket.input.id, output = aws_s3_bucket.output.id, frontend = aws_s3_bucket.frontend.id }
  bucket   = each.value
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_versioning" "data" {
  for_each = { input = aws_s3_bucket.input.id, output = aws_s3_bucket.output.id, frontend = aws_s3_bucket.frontend.id }
  bucket   = each.value
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  for_each = { input = aws_s3_bucket.input.id, output = aws_s3_bucket.output.id, frontend = aws_s3_bucket.frontend.id }
  bucket   = each.value
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  for_each = { input = aws_s3_bucket.input.id, output = aws_s3_bucket.output.id }
  bucket   = each.value
  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload { days_after_initiation = 3 }
  }
}

resource "aws_s3_bucket_cors_configuration" "input" {
  bucket = aws_s3_bucket.input.id
  cors_rule {
    allowed_headers = ["Content-Type", "Content-Length"]
    allowed_methods = ["PUT", "HEAD"]
    allowed_origins = ["https://${aws_cloudfront_distribution.frontend.domain_name}"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_cors_configuration" "output" {
  bucket = aws_s3_bucket.output.id
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["https://${aws_cloudfront_distribution.frontend.domain_name}"]
    expose_headers  = ["Content-Disposition", "Content-Length", "Content-Type"]
    max_age_seconds = 3000
  }
}

resource "aws_dynamodb_table" "jobs" {
  name         = "${local.name_prefix}-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_sub"
  range_key    = "job_id"

  attribute {
    name = "user_sub"
    type = "S"
  }
  attribute {
    name = "job_id"
    type = "S"
  }

  point_in_time_recovery { enabled = true }
  server_side_encryption { enabled = true }
}

resource "aws_dynamodb_table" "worker_slots" {
  name         = "${local.name_prefix}-worker-slots"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "slot_id"
  attribute {
    name = "slot_id"
    type = "S"
  }
  server_side_encryption { enabled = true }
}

resource "aws_dynamodb_table_item" "worker_slots" {
  for_each   = toset(["slot-0", "slot-1"])
  table_name = aws_dynamodb_table.worker_slots.name
  hash_key   = aws_dynamodb_table.worker_slots.hash_key
  item       = jsonencode({ slot_id = { S = each.value } })
}

resource "aws_sqs_queue" "jobs_dlq" {
  name                      = "${local.name_prefix}-jobs-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "jobs" {
  name                       = "${local.name_prefix}-jobs"
  visibility_timeout_seconds = 900
  message_retention_seconds  = 345600
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.jobs_dlq.arn
    maxReceiveCount     = 5
  })
}
