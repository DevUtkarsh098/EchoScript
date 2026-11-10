# AWS deployment

This is the active single-account deployment path for the new AWS account in `us-west-2`. The previous three-account/k3s procedure is retained in Git history and handover notes for context; it is not the selected deployment. See [the architecture and cost proposal](deployment-proposal.md) for the approved design and assumptions.

**The ECS Express Mode architecture and revised `$85–$110/month` planning estimate are proposed and await owner approval.** The account is authenticated. The separately approved bootstrap stage is complete: encrypted/versioned Terraform state bucket, DynamoDB lock table, and immutable API/worker ECR repositories exist in account `598391748654`, region `us-west-2`. No application services or user-facing resources have been provisioned.

## Components

- CloudFront serves a private S3-hosted React application over HTTPS.
- Cognito handles user sign-in with authorization code and PKCE.
- ECS Express Mode hosts the FastAPI API on Fargate behind an HTTPS Application Load Balancer. AWS closed App Runner to new customers; see the [revised architecture and cost proposal](deployment-proposal.md).
- DynamoDB stores owner-keyed job state. Private S3 stores uploaded audio and TXT/SRT/VTT results.
- SQS and a dead-letter queue feed a Lambda dispatcher and Step Functions workflow.
- Fargate runs one CPU-only faster-whisper task per job. No GPU or inbound worker access is configured.
- ECR stores immutable API and worker images. CloudWatch logs and an AWS Budget are provisioned by Terraform.

## Prerequisites for a later deployment session

1. Configure AWS IAM Identity Center or another short-lived role profile locally for the **new** account. Never provide credentials in chat or commit them.
2. Confirm the active profile, account ID, and `us-west-2` locally before using AWS commands. Confirm billing is active and quotas permit the resources in the proposal.
3. Bootstrap a unique encrypted S3 Terraform state bucket and DynamoDB lock table from `infrastructure/terraform/bootstrap-state`. This bootstrap begins with local state, then migrates its own state into S3. It prevents destruction of the bucket and lock table. The state bucket has versioning, public access blocked, and a TLS-only bucket policy. See the bootstrap README for commands.
4. Install Terraform `>=1.7`, AWS CLI, Docker, Node/npm, and Trivy.
5. Provide an optional budget-alert email address through a local ignored `terraform.tfvars` file if AWS Budgets notifications are wanted.

## Deployment sequence

Do not proceed beyond the existing bootstrap resources until the owner approves the revised architecture and cost range. After approval, each application resource-creating step still requires a reviewed plan and the applicable provisioning approval.

1. The bootstrap backend and ECR repositories already exist. Use the configured backend values in the ignored `backend.hcl` and verify the state points to the new account's state bucket before initializing the application root. Never reuse state from the previous AWS account.
2. After architecture approval and Terraform updates, copy `terraform.tfvars.example` to the ignored `terraform.tfvars`, set `image_tag` to the Git SHA that will be published, and set the budget-alert address if notifications are wanted. Confirm the existing ECR repositories are tracked/imported correctly before planning; do not create duplicates.
3. Run `scripts/publish-images.sh YOUR_GIT_SHA` from a clean checkout at that exact commit. It checks that the active AWS account and region match the Terraform outputs, runs the source secret scan, builds Linux AMD64 images, blocks HIGH/CRITICAL Trivy findings, and pushes immutable tags.
4. Set `image_tag` to the published SHA, then create and review a fresh full Terraform plan. Stop for owner review if the plan deletes, replaces, or exposes unexpected resources. Apply only after explicit approval.
5. Run `scripts/deploy-frontend.sh`. It checks the current account and region against Terraform, builds with the new API and Cognito outputs, syncs the private web bucket, then invalidates CloudFront.
6. Complete the real-audio acceptance workflow in `HANDOFF_FOR_NEXT_DEVELOPER.md`, including actual authentication, cross-user rejection, faster-whisper processing, and all three downloadable outputs.
7. Record the public frontend/API URLs, image SHA, test evidence, deployed resources, and actual cost-monitoring configuration. Do not describe the app as deployed until the full acceptance test passes.

## State, recovery, and cleanup

Use a new-account encrypted and versioned S3 backend with locking. Keep Terraform state and prior immutable image tags for recovery. Rollback means redeploying a known-good API/worker SHA and frontend bundle while preserving user data. S3 data deletion and Terraform destroy are separate destructive actions and require explicit approval. Check the AWS Budget and actual billing after the first usage cycle; the planning range is not a cost cap.
