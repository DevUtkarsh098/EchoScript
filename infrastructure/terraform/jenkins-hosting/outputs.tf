output "node_ids" { value = { for name, node in aws_instance.node : name => node.id } }
output "controller_private_ip" { value = aws_instance.node["controller"].private_ip }
output "controller_volume_id" { value = aws_ebs_volume.controller.id }
output "ssm_transfer_bucket" { value = aws_s3_bucket.transfer.id }
output "jenkins_backup_bucket" { value = aws_s3_bucket.jenkins_backup.id }
output "bootstrap_secret_arns" { value = { for name, secret in aws_secretsmanager_secret.node : name => secret.arn } }
output "deployment_role_arns" { value = { for name, role in aws_iam_role.deployment : name => role.arn } }
output "container_repositories" { value = { for name, repository in aws_ecr_repository.jenkins : name => repository.repository_url } }
output "controller_url" { value = "https://jenkins.internal:8443" }
