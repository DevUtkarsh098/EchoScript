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

### Local branch verification, 2026-11-12

- Built API, worker and frontend images and started a separate loopback-only local Compose stack with isolated test data. Demo upload/start/TXT-SRT-VTT/audio downloads and invalid-upload rejection passed. All 34 automated tests passed; Terraform backend-free checks and disposable local Ansible idempotence also passed.
- Added missing ESLint configuration and removed unused imports/parameter; frontend build, tests and lint passed (two fast-refresh warnings). Optional local recap rendering failed due to the API image's absent `ffmpeg`; real speech inference and browser interaction were not verified. No AWS deployment or application-data changes occurred. Full results: [local-verification.md](local-verification.md).

### Cost approval follow-up, 2026-11-11

- Owner approved the proposed $70–$85/month Jenkins hosting increment, $220/month account budget and $2 disposable AWS test with “cost approved do that”; reference `owner-chat-2026-11-11-cost-approved`. Updated the cost model and status; no further cost confirmation is required within this scope.
- AWS CLI still lists no profiles. Requested the developer's own `giri` Identity Center configuration/login; browser automation was unavailable. No credentials were copied and no cloud provisioning, backend initialization or budget update occurred. Verified contact email, backend, AMI and policies still require authenticated access. Runtime implementation and live acceptance checks remain pending.

### AWS-only hosting follow-up, 2026-11-11

- Applied the revised instruction that Jenkins must run in AWS, not on a laptop. Stopped the old local controller and retired its launcher files while retaining historical evidence.
- Prepared a separate, account/region-pinned `jenkins-hosting` Terraform proposal with explicit cost/budget/email/policy preconditions, independent state key in the same existing backend, three isolated hosts and a disabled optional AWS test host. No AWS backend init, plan/apply or provisioning occurred.
- Added a parameterized SSM inventory and guarded `jenkins_host` Ansible foundation. Lint/syntax passed, but AWS check/apply/idempotence has not run. Cost approval was subsequently received; own AWS login is pending. Production controller/HTTPS/agent runtime and recovery testing remain pending.
- Added EC2 instance-profile-to-job-role support, fixed root-owned 900-second machine profiles and security tests; 18 CI safety tests now pass. Static keys and developer SSO on Jenkins remain prohibited.
- Verified public Oregon EC2 rates and recorded a reproducible cost model: $69.47 nominal / $70–$85 expected monthly CI increment; $155–$195 combined application/account estimate. Proposed account budget is $220 plus a $2 one-off AWS test allowance, neither approved yet.
- Updated handover/status/deployment documentation to respect the owner's confirmed working transcription workflow. The former fresh-job acceptance gap is historical, not outstanding. Pipeline smoke tests remain a separate future CI requirement.

### giri CI/CD implementation, 2026-11-11

- Created `giri` from `imran` at `c528ca0`, preserving history. The owner reports that the transcription workflow is working; its implementation and data were left intact.
- Replaced obsolete Jenkins delivery with isolated PR validation and a separate OIDC-only, approval-gated ECS/Fargate release job. Added saved-plan scope/checksum/encryption guards, immutable ECR publication, frontend release capsules, and a fresh authenticated smoke script. No AWS modification or backend initialization was performed during local implementation.
- Retired the stale infra/runtime jobs, Kubernetes selector-switch scripts, k3s playbook, and static production inventory. Added Docker tooling and a local-only reusable Ansible workspace role.
- Docker toolchain build and Ansible lint/syntax/check/apply/idempotence passed. Fifteen CI safety tests exercise backend mismatch rejection, data-resource plan rejection, secret-log suppression, unsafe bundle rejection, scoped IAM policies, encrypted plan diagnostics, and the actual frontend rollback script against local test doubles. Ten API, two worker and three frontend tests passed independently.
- Initial security gates exposed old Nginx/OS and frontend build/dependency vulnerabilities. Updated the Nginx runtime, frontend build/test tooling and lockfile, and removed unused form/validation dependencies. Final independent API/worker/frontend image and frontend dependency scans each reported zero HIGH/CRITICAL findings; seven moderate development-tool advisories remain visible.
- Real local Jenkins build #1 ran at `http://localhost:8088/job/echoscript-validation/1/`, commit `a047a4d725ec13f00f8c2cdb6241398799d475d5`. It passed source/frontend/Terraform checks and stopped at Docker image build because approved agent access was unavailable. The host socket mount was rejected by automatic approval review; no bypass was attempted.
- Final implementation build #2 ran at `http://localhost:8088/job/echoscript-validation/2/`, commit `c6700974f547bd22b1fb9e0cf763f3016af67da9`. All 15 CI regression tests, frontend build/3 auth tests/HIGH audit gate, and Terraform validation passed. It also failed at Docker access, so a successful full Jenkins pipeline and production release are still pending approval/configuration.
- Full evidence, Jenkins run status, and production configuration blockers are recorded in [ci-verification.md](ci-verification.md); operational instructions and IAM review requirements are in [ci-cd.md](ci-cd.md).

### Prior deployment evidence from imran

- Recovered the single-account AWS deployment path and applied infrastructure in the same account and region. The infrastructure plan applied 75 resources with no changes or deletions at that point.
- Fixed the Cognito callback navigation loop; updated frontend assets were published and the CloudFront invalidation completed. The user subsequently confirmed successful sign-in.
- Fixed audio upload signing to use the regional S3 endpoint with Signature V4 and virtual-host addressing; configured the exact CloudFront origin and required S3 CORS methods/headers. An authenticated synthetic MP3 upload succeeded.
- Added the worker's missing `requests` dependency and pinned a compatible PyAV version (`18.1.0`) after the prior version conflicted with faster-whisper. A local PyAV decode check succeeded on the sample.
- Ran faster-whisper in the deployed worker. DynamoDB showed `TRANSCRIBED`, and transcript, SRT, and VTT objects were stored in S3.
- Fixed Step Functions input loss after the ECS transcription task by discarding the task result from workflow state (`ResultPath = null`), preserving `job_id` for the release-slot step. That historical check used an already-transcribed job. The owner subsequently confirmed that transcription works; this is no longer an outstanding application acceptance gap.
- Built/published immutable container images and ran Trivy gates. Secret scanning passed and the images had zero HIGH/CRITICAL findings. The worker image was assembled with the compatible PyAV wheel due to slow Docker downloads; perform a clean reproducible build from the checked-in Dockerfile as part of takeover.
- API health returned `{"status":"ok"}`. This does not establish full end-to-end acceptance.

## Remaining checks

- After AWS Jenkins hosting is approved/provisioned, record its fresh authenticated deployment smoke test. This is CI evidence, not a request to repeat the owner's accepted application test.
- Preserve the working transcript/subtitle download behavior; verify CI identity isolation without changing application processing.
- Exercise worker failure, retry, slot release, and recovery. Test representative speech and supported formats.
- Decide whether the deployed PyAV decoder meets the original FFmpeg requirement or add and test the required FFmpeg processing step.
- Review actual AWS costs and configure a budget alert. Current estimate is `$85–$110/month`; Terraform's `$100/month` budget has no alert recipient.
- AWS-hosted Jenkins/Ansible are not operational yet. `giri` replaced the stale deployment paths and added tested CI controls. Costs are approved, but own AWS access is pending; no cloud Jenkins resources or disposable AWS test host have been provisioned. See [jenkins-aws-design.md](jenkins-aws-design.md).
- Verify rollback, monitoring/alert delivery, SonarQube/ZAP if adopted, and the separate video/provider workflow.

## Repository and runtime notes

- The last deployed-code commit before this documentation update was `f689f2f` (`Preserve workflow input after transcription`).
- Handover branch: `imran` on <https://github.com/Girirraju/EchoScript/tree/imran>. Review and merge using a pull request; preserve history.
- Each incoming developer must use their own AWS IAM Identity Center assignment. Never transfer SSO sessions, device codes, passwords, or static credentials.
- Use Docker only; do not use Podman. Do not destroy infrastructure, migrate the current Terraform state, or delete user data during takeover.
