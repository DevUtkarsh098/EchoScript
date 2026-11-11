# Terraform deployment

The active production root is `single-account`, in existing account `598391748654`, region `us-west-2`. Use its existing encrypted S3 backend and DynamoDB lock table. Confirm their live metadata before initialization; do not rerun bootstrap, migrate state, or create a new workspace/account during developer handover.

`jenkins-hosting` is a **proposed, unprovisioned** root for new AWS-only CI hosts. It uses the same confirmed existing backend bucket/lock with the separate key `echoscript/jenkins-hosting/terraform.tfstate`; it never reuses or replaces the application's state key. Cost/budget/email/policy approval gates remain unset. Read [the costed design](../../docs/jenkins-aws-design.md) before any resource-creating operation. Do not mistake backend-free validation for an approved live plan/apply.

`account1`, `account2`, `account3`, and their historical CIDR/peering design are not deployed production roots and are excluded from Jenkins. `bootstrap-state` is retained for specifically approved state recovery, not ordinary CI. Never run `terraform destroy` or delete application data.

PRs run formatting and `init -backend=false`/validation using the committed provider lock. Releases archive an encrypted plan against existing state and require an explicit Jenkins approval before applying the same saved plan. See [the CI/CD runbook](../../docs/ci-cd.md).

