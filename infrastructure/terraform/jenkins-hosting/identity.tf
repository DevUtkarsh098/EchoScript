resource "aws_secretsmanager_secret" "node" {
  for_each                = local.nodes
  name                    = "echoscript/jenkins/${each.key}/bootstrap"
  recovery_window_in_days = 30
  description             = "New Jenkins machine bootstrap secret only; populate outside Terraform using own approved access"
  depends_on              = [terraform_data.approval]
}

resource "aws_iam_role" "node" {
  for_each = local.nodes
  name     = "echoscript-jenkins-${each.key}-host"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
  depends_on = [terraform_data.approval]
}

resource "aws_iam_role_policy_attachment" "ssm" {
  for_each   = local.nodes
  role       = aws_iam_role.node[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "host" {
  for_each = local.nodes
  name     = "jenkins-host-bootstrap-only"
  role     = aws_iam_role.node[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Effect   = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"],
        Resource = "${aws_cloudwatch_log_group.jenkins.arn}:*"
      },
      {
        Effect   = "Allow", Action = ["secretsmanager:GetSecretValue"],
        Resource = aws_secretsmanager_secret.node[each.key].arn
      },
      {
        Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*"
      },
      {
        Effect   = "Allow", Action = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"],
        Resource = [for repository in aws_ecr_repository.jenkins : repository.arn]
      }
      ], each.key == "controller" ? [{
        Effect   = "Allow", Action = ["s3:PutObject", "s3:GetObject"],
        Resource = "${aws_s3_bucket.jenkins_backup.arn}/jenkins-home/*"
        }] : [], each.key == "controller" ? [{
        Effect   = "Allow", Action = ["secretsmanager:GetSecretValue", "secretsmanager:PutSecretValue"],
        Resource = [aws_secretsmanager_secret.node["validation"].arn, aws_secretsmanager_secret.node["release"].arn]
        }] : [], each.key == "release" ? [{
        Effect = "Allow", Action = ["sts:AssumeRole"], Resource = [for role in aws_iam_role.deployment : role.arn]
    }] : [])
  })
}

resource "aws_iam_instance_profile" "node" {
  for_each = local.nodes
  name     = aws_iam_role.node[each.key].name
  role     = aws_iam_role.node[each.key].name
}

resource "aws_iam_role" "deployment" {
  for_each             = local.deployment_roles
  name                 = "echoscript-jenkins-${each.key}"
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow", Principal = { AWS = aws_iam_role.node["release"].arn }, Action = "sts:AssumeRole"
    }]
  })
  depends_on = [terraform_data.approval]
}

resource "aws_iam_role_policy" "deployment" {
  for_each = local.deployment_roles
  name     = "reviewed-application-release-scope"
  role     = aws_iam_role.deployment[each.key].id
  policy   = lookup(var.application_role_policies, each.key, "{\"Version\":\"2012-10-17\",\"Statement\":[]}")
}
