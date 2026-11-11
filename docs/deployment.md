# AWS deployment

This is the active single-account deployment path for the new AWS account in `us-west-2`. The previous three-account/k3s procedure is retained in Git history and handover notes for context; it is not the selected deployment. See [the architecture and cost proposal](deployment-proposal.md) for the approved design and assumptions.

**Core deployment provisioned on 2026-11-11** in account `598391748654`, region `us-west-2`, from commit `81092db`. Terraform created 75 resources. The React frontend is published at <https://dtdd5d335m3k2.cloudfront.net>; the API is at <https://ec-4762c5d9c1fa4c50a19bed3b76373799.ecs.us-west-2.on.aws>. The API `/ready` endpoint returned `200`, its ECS task and ALB target are healthy, and the frontend returned `200`. Authenticated real-audio acceptance, cross-user authorization, and TXT/SRT/VTT download checks remain outstanding, so the deployment is provisioned but not yet end-to-end accepted.

## Components

- CloudFront serves a private S3-hosted React application over HTTPS.
- Cognito handles user sign-in with authorization code and PKCE.
- ECS Express Mode hosts the FastAPI API on Fargate behind an HTTPS Application Load Balancer. AWS closed App Runner to new customers; see the [revised architecture and cost proposal](deployment-proposal.md).
- DynamoDB stores owner-keyed job state. Private S3 stores uploaded audio and TXT/SRT/VTT results.
- SQS and a dead-letter queue feed a Lambda dispatcher and Step Functions workflow.
- Fargate runs one CPU-only faster-whisper task per job. Audio is decoded directly through PyAV; no FFmpeg package, GPU, or inbound worker access is configured.
- ECR stores immutable API and worker images. CloudWatch logs and an AWS Budget are provisioned by Terraform.

## Prerequisites for future updates

1. Configure AWS IAM Identity Center or another short-lived role profile locally for the **new** account. Never provide credentials in chat or commit them.
2. Confirm the active profile, account ID, and `us-west-2` locally before using AWS commands. Confirm billing is active and quotas permit the resources in the proposal.
3. Bootstrap a unique encrypted S3 Terraform state bucket and DynamoDB lock table from `infrastructure/terraform/bootstrap-state`. This bootstrap begins with local state, then migrates its own state into S3. It prevents destruction of the bucket and lock table. The state bucket has versioning, public access blocked, and a TLS-only bucket policy. See the bootstrap README for commands.
4. Install Terraform `>=1.7`, AWS CLI, Docker, Node/npm, and Trivy.
5. Provide an optional budget-alert email address through a local ignored `terraform.tfvars` file if AWS Budgets notifications are wanted.

## Deployment record and next acceptance steps

The user directed deployment to proceed in this session. The revised ECS Express Mode architecture was applied through a fresh reviewed plan. The image publishing gate ran the Trivy source secret scan and HIGH/CRITICAL image scan before publication.

1. Bootstrap state and ECR repositories are in the new account; application Terraform state remains in the encrypted S3 backend with DynamoDB locking.
2. Immutable API and worker images tagged `81092db` were pushed to the account's ECR repositories.
3. Terraform applied the full plan: 75 resources added, none changed or destroyed. CloudFront, Cognito, ECS Express, Fargate worker orchestration, private buckets, queues, tables, logs, and a `$100/month` AWS Budget were provisioned. No budget email is configured.
4. The frontend was built with the deployed API and Cognito settings, synced to the private S3 origin, and a CloudFront invalidation was requested.
5. Complete the authenticated real-audio acceptance workflow in `HANDOFF_FOR_NEXT_DEVELOPER.md`: sign in, verify cross-user rejection, process a real audio file, and download TXT, SRT, and VTT outputs. Record the results before calling the app end-to-end accepted.

## State, recovery, and cleanup

Use a new-account encrypted and versioned S3 backend with locking. Keep Terraform state and prior immutable image tags for recovery. Rollback means redeploying a known-good API/worker SHA and frontend bundle while preserving user data. S3 data deletion and Terraform destroy are separate destructive actions and require explicit approval. Check the AWS Budget and actual billing after the first usage cycle; the planning range is not a cost cap.
