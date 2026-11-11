resource "aws_s3_bucket" "transfer" {
  bucket        = "echoscript-598391748654-jenkins-ssm-transfer"
  force_destroy = false
  depends_on    = [terraform_data.approval]
}

resource "aws_s3_bucket_public_access_block" "transfer" {
  bucket                  = aws_s3_bucket.transfer.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "transfer" {
  bucket = aws_s3_bucket.transfer.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_policy" "transfer_tls" {
  bucket = aws_s3_bucket.transfer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Deny", Principal = "*", Action = "s3:*",
      Resource  = [aws_s3_bucket.transfer.arn, "${aws_s3_bucket.transfer.arn}/*"],
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}

resource "aws_s3_bucket_lifecycle_configuration" "transfer" {
  bucket = aws_s3_bucket.transfer.id
  rule {
    id     = "expire-ci-transfer-scratch-only"
    status = "Enabled"
    filter {}
    expiration { days = 1 }
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
}

resource "aws_ecr_repository" "jenkins" {
  for_each             = toset(["controller", "agent"])
  name                 = "echoscript/jenkins/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration { scan_on_push = true }
  depends_on = [terraform_data.approval]
}

resource "aws_backup_vault" "jenkins" {
  name       = "echoscript-jenkins-only"
  depends_on = [terraform_data.approval]
}

resource "aws_iam_role" "backup" {
  name = "echoscript-jenkins-backup"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "backup.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
  depends_on = [terraform_data.approval]
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_backup_plan" "jenkins" {
  name = "echoscript-jenkins-daily"
  rule {
    rule_name         = "jenkins-data-only"
    target_vault_name = aws_backup_vault.jenkins.name
    schedule          = "cron(0 18 * * ? *)"
    lifecycle { delete_after = 14 }
  }
}

resource "aws_backup_selection" "jenkins" {
  name         = "controller-data-volume-only"
  plan_id      = aws_backup_plan.jenkins.id
  iam_role_arn = aws_iam_role.backup.arn
  resources    = [aws_ebs_volume.controller.arn]
  depends_on   = [aws_iam_role_policy_attachment.backup]
}
