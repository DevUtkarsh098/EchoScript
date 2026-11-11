# AWS deployment

Updated: 2026-11-11

## Active environment

- AWS account: `598391748654` (the account remains the same during developer handover).
- Region: `us-west-2`.
- IAM Identity Center start URL: <https://identitycenter.amazonaws.com/ssoins-7907428395ee23f8>. Each developer must receive their own assignment and use short-lived credentials; never share SSO tokens or credentials.
- Frontend: <https://dtdd5d335m3k2.cloudfront.net>.
- API: <https://ec-4762c5d9c1fa4c50a19bed3b76373799.ecs.us-west-2.on.aws>.
- Terraform root: `infrastructure/terraform/single-account`; state bootstrap/recovery root: `infrastructure/terraform/bootstrap-state`.

## Architecture

CloudFront serves a React frontend from private S3. Cognito provides browser sign-in. ECS Express Mode/Fargate runs the FastAPI API; private S3 stores audio and transcript outputs; DynamoDB tracks jobs. SQS, Lambda, and Step Functions dispatch and track jobs, while a Fargate task runs faster-whisper. ECR stores immutable images, and CloudWatch receives logs. Terraform manages the AWS application resources.

## Current verification

The AWS environment is provisioned and live. The owner has confirmed that transcription is working. Earlier synthetic-upload/transcription checks and the workflow state-preservation fix remain historical evidence; the former fresh-job acceptance gap is not outstanding. Preserve this application behavior. Future Jenkins deployment smoke tests establish CI delivery evidence separately.

Production endpoints and deployment evidence, including the remaining acceptance checks, are in [the developer handover](../HANDOFF_FOR_NEXT_DEVELOPER.md) and [the change log](developer-handover-changes.md).

## Cost and safety

Terraform configured a `$100/month` AWS Budget without an alert email. The current planning estimate is `$85–$110/month`; check actual billing and reconcile the estimate with the budget. The estimate is not a spending cap.

Do not run `terraform destroy`, delete user data, recreate/migrate the existing state, or deploy the stale Kubernetes/k3s examples. Inspect the account, region, backend, and plan before any modifying Terraform operation. Use Docker only; do not use Podman.

## Jenkins and Ansible status

On `giri`, the obsolete Jenkins/k3s paths have been retired. The replacement pipeline uses the active single-account root, exact scanned immutable images, OIDC-only machine identities, an encrypted saved plan and explicit approval, preserved frontend bundles, and authenticated smoke checks. The Ansible role configures only a disposable local agent workspace and passed lint/syntax/check/idempotence tests. Production Jenkins access and deployment/rollback results remain unverified. Use [the CI/CD runbook](ci-cd.md) and [recorded evidence](ci-verification.md); do not run historical deployment paths.
