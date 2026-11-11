# Developer handover change log

Updated: 2026-11-11

This document records the recovery, deployment, and verification changes available to the incoming developer. The AWS account stays the same; only the developer and their individual access assignment change.

## Current cloud environment

- Account `598391748654`, region `us-west-2`; AWS IAM Identity Center start URL: <https://identitycenter.amazonaws.com/ssoins-7907428395ee23f8>.
- Production frontend: <https://dtdd5d335m3k2.cloudfront.net>.
- Production API: <https://ec-4762c5d9c1fa4c50a19bed3b76373799.ecs.us-west-2.on.aws>.
- Terraform single-account deployment root: `infrastructure/terraform/single-account`.
- Deployed application uses CloudFront/private S3, Cognito, ECS Express Mode/Fargate, DynamoDB, SQS/DLQ, Lambda, Step Functions, ECR, and CloudWatch.

## Changes and evidence

### giri CI/CD implementation, 2026-11-11

- Created `giri` from `imran` at `c528ca0`, preserving history. The owner reports that the transcription workflow is working; its implementation and data were left intact.
- Replaced obsolete Jenkins delivery with isolated PR validation and a separate OIDC-only, approval-gated ECS/Fargate release job. Added saved-plan scope/checksum/encryption guards, immutable ECR publication, frontend release capsules, and a fresh authenticated smoke script. No AWS modification or backend initialization was performed during local implementation.
- Retired the stale infra/runtime jobs, Kubernetes selector-switch scripts, k3s playbook, and static production inventory. Added Docker tooling and a local-only reusable Ansible workspace role.
- Docker toolchain build and Ansible lint/syntax/check/apply/idempotence passed. CI safety tests exercise backend mismatch rejection, data-resource plan rejection, secret-log suppression, unsafe bundle rejection, and the actual frontend rollback script against local test doubles.
- Full evidence, Jenkins run status, and production configuration blockers are recorded in [ci-verification.md](ci-verification.md); operational instructions and IAM review requirements are in [ci-cd.md](ci-cd.md).

### Prior deployment evidence from imran

- Recovered the single-account AWS deployment path and applied infrastructure in the same account and region. The infrastructure plan applied 75 resources with no changes or deletions at that point.
- Fixed the Cognito callback navigation loop; updated frontend assets were published and the CloudFront invalidation completed. The user subsequently confirmed successful sign-in.
- Fixed audio upload signing to use the regional S3 endpoint with Signature V4 and virtual-host addressing; configured the exact CloudFront origin and required S3 CORS methods/headers. An authenticated synthetic MP3 upload succeeded.
- Added the worker's missing `requests` dependency and pinned a compatible PyAV version (`18.1.0`) after the prior version conflicted with faster-whisper. A local PyAV decode check succeeded on the sample.
- Ran faster-whisper in the deployed worker. DynamoDB showed `TRANSCRIBED`, and transcript, SRT, and VTT objects were stored in S3.
- Fixed Step Functions input loss after the ECS transcription task by discarding the task result from workflow state (`ResultPath = null`), preserving `job_id` for the release-slot step. A following execution succeeded as a no-op because its job was already transcribed; test a new job to prove a full successful run.
- Built/published immutable container images and ran Trivy gates. Secret scanning passed and the images had zero HIGH/CRITICAL findings. The worker image was assembled with the compatible PyAV wheel due to slow Docker downloads; perform a clean reproducible build from the checked-in Dockerfile as part of takeover.
- API health returned `{"status":"ok"}`. This does not establish full end-to-end acceptance.

## Remaining checks

- Submit one fresh audio job and capture proof that the same workflow execution performs inference and ends `SUCCEEDED`.
- Download and inspect TXT, SRT, and VTT via the authenticated UI; verify unauthenticated and cross-user requests are rejected.
- Exercise worker failure, retry, slot release, and recovery. Test representative speech and supported formats.
- Decide whether the deployed PyAV decoder meets the original FFmpeg requirement or add and test the required FFmpeg processing step.
- Review actual AWS costs and configure a budget alert. Current estimate is `$85–$110/month`; Terraform's `$100/month` budget has no alert recipient.
- Jenkins and Ansible are not operational. Existing Jenkinsfiles reference missing scripts and obsolete Kubernetes paths. The Ansible sample playbook configures k3s on static hosts. The detailed implementation steps and safety constraints are in [the developer handover](../HANDOFF_FOR_NEXT_DEVELOPER.md).
- Verify rollback, monitoring/alert delivery, SonarQube/ZAP if adopted, and the separate video/provider workflow.

## Repository and runtime notes

- The last deployed-code commit before this documentation update was `f689f2f` (`Preserve workflow input after transcription`).
- Handover branch: `imran` on <https://github.com/Girirraju/EchoScript/tree/imran>. Review and merge using a pull request; preserve history.
- Each incoming developer must use their own AWS IAM Identity Center assignment. Never transfer SSO sessions, device codes, passwords, or static credentials.
- Use Docker only; do not use Podman. Do not destroy infrastructure, migrate the current Terraform state, or delete user data during takeover.
