# EchoScript developer handover

Updated: 2026-11-11

## Takeover summary

### CI/CD work on giri

Current requirement: Jenkins must be hosted in this AWS account/region. The laptop harness was stopped and retired. Review [the AWS cost/access design](docs/jenkins-aws-design.md) before provisioning: expected **$70–$85/month extra**, proposed **$220 account budget**, and **$2 disposable AWS test allowance**. The new hosting Terraform, SSM inventory, host foundation and native 15-minute machine-role path are prepared/static-tested; no AWS hosting resources or AWS target tests exist yet. Cost approval and verified own access/contact email are still required.

`giri` was created from `imran` at `c528ca0` for Jenkins/Ansible implementation. The project owner reports transcription is working; the code path and application data are preserved. The stale Jenkins/k3s deployment paths have been retired and replaced with the implementation in [docs/ci-cd.md](docs/ci-cd.md). Local verification and live-delivery blockers are recorded in [docs/ci-verification.md](docs/ci-verification.md). No production Jenkins machine identity or backend access has been supplied, so do not treat the new files or local tests as a completed AWS deployment.

The AWS account and deployment remain the same; only the developer is changing. Continue work in AWS account `598391748654`, region `us-west-2`. Do not create another AWS account, migrate Terraform state, rebuild the platform in a different account, or use credentials from the historical suspended account.

The production frontend is <https://dtdd5d335m3k2.cloudfront.net>. The FastAPI API is <https://ec-4762c5d9c1fa4c50a19bed3b76373799.ecs.us-west-2.on.aws>. Cognito sign-in was confirmed in the browser. A synthetic MP3 uploaded successfully and faster-whisper generated transcript, SRT, and VTT objects in the private output bucket. See [the deployment change log](docs/developer-handover-changes.md) for the exact work and evidence.

The project owner has confirmed that the transcription workflow is working. The earlier fresh-job acceptance gap is historical and is not an outstanding application blocker. Preserve the working service and its data. A future authenticated Jenkins deployment smoke test is separate CI evidence and must not be confused with the owner's application acceptance.

## Account access and safety

- AWS account: `598391748654`.
- Region: `us-west-2`.
- AWS IAM Identity Center start URL: <https://identitycenter.amazonaws.com/ssoins-7907428395ee23f8>.
- The incoming developer must be granted their own Identity Center assignment to this same account. Do not share the current developer's SSO session, password, device code, or credentials. Use short-lived role credentials and least privilege; the previous developer used `AdministratorAccess`, which should not be copied as the default for Jenkins.
- Terraform's existing encrypted remote state and lock table belong to this deployment. Inspect the configured backend and account before any Terraform command that can modify resources. Do not rerun bootstrap or migrate state unless a specific recovery need is established.
- Never run `terraform destroy`, delete data buckets, or repurpose the historical account as part of this takeover.
- Use Docker for container work; do not use Podman.

## Current architecture

- CloudFront serves the frontend from a private S3 bucket.
- Cognito provides browser sign-in; the API validates JWTs and scopes jobs to their owner.
- ECS Express Mode/Fargate hosts the FastAPI API.
- S3 stores private input audio and TXT/SRT/VTT outputs; DynamoDB stores job state.
- SQS and a dead-letter queue feed Lambda/Step Functions orchestration; a Fargate task runs faster-whisper.
- ECR stores immutable API and worker images. CloudWatch holds service and worker logs. Terraform manages the AWS application resources.
- The active Terraform root is `infrastructure/terraform/single-account`; `infrastructure/terraform/bootstrap-state` is only for state bootstrap/recovery. The historical `account1`, `account2`, `account3`, Kubernetes/k3s, and static Ansible examples are not the deployed production path.

The frontend and API URLs and the approved AWS account are also recorded in [docs/deployment.md](docs/deployment.md). The deployment plan's current cost estimate is approximately `$85–$110/month`, depending on usage. Terraform configured a `$100/month` budget, but no alert email is configured; review actual AWS billing and resolve the estimate/threshold mismatch.

## Verified behavior and remaining acceptance

### Verified

- The deployed Cognito sign-in flow completed successfully.
- An authenticated browser upload of `echoscript-upload-check.mp3` reached the private input bucket. The earlier upload failure was caused by a global S3 endpoint redirect; presigning now uses the regional us-west-2 endpoint and S3 CORS allows the frontend origin with the required headers.
- faster-whisper ran in the worker and wrote transcript, SRT, and VTT objects. DynamoDB recorded `TRANSCRIBED` and output references.
- A state-machine input-preservation fix (`ResultPath = null` on `RunTranscription`) is deployed. A subsequent execution succeeded for the already-transcribed job, skipping inference as designed.
- Docker image builds and the repository publishing gates were run. Secret scanning passed, and Trivy reported zero HIGH/CRITICAL findings on the published API and worker images. Worker audio decoding was checked locally with PyAV 18.1.0.
- The API health endpoint returned `{"status":"ok"}`.

### Do next

1. After AWS Jenkins hosting/cost approval, run the pipeline's fresh authenticated transcription smoke test and record its job/workflow/output evidence. This verifies CI deployment, not an unresolved owner acceptance gap.
2. Preserve the owner-tested upload and TXT/SRT/VTT download behavior; do not alter application processing during Jenkins setup.
3. Verify unauthenticated requests are rejected and cross-user job, audio, and output access is denied.
4. Exercise an intentional worker failure, the supported retry path, and recovery after worker restart. Confirm failed jobs do not retain a worker-slot lease.
5. Test representative real speech and supported audio formats. The verified sample was synthetic and does not establish transcription quality on ordinary recordings.
6. Reconcile the original handover's FFmpeg requirement: the deployed worker decodes with PyAV and does not install a separate FFmpeg executable. Either document why this satisfies the media-preparation requirement or implement/test a dedicated FFmpeg step.

## Jenkins implementation work

Production Jenkins delivery is **not operationally verified**. On `giri`, use `ci/Jenkinsfile.validation` and `ci/Jenkinsfile.delivery`, described in [the CI/CD runbook](docs/ci-cd.md). The old infra/runtime entrypoints now fail closed instead of running obsolete deployments.

Historical mismatches found on `imran` and retired by the `giri` implementation:

- `ci/Jenkinsfile.infra` loops over historical `account*` roots and invokes missing `ci/scripts/terraform-apply.sh`; it does not select the live `single-account` root.
- `ci/Jenkinsfile.delivery` invokes missing `ci/scripts/push-images.sh` and `ci/scripts/deploy-color.sh`, and its blue/green Kubernetes deployment does not match the live ECS Express Mode service.
- `ci/Jenkinsfile.runtime` invokes missing `ci/scripts/deploy-runtime.sh` and references missing `infrastructure/kubernetes/monitoring`.
- No Jenkins controller/agent credentials, IAM role trust, or successful pipeline run have been verified.

Implement and verify a Jenkins pipeline for the *current* architecture:

1. Pull request/validation stages: frontend build, API and worker tests, Terraform fmt/validate for the single-account root, Ansible lint/syntax/check-mode tests, secret scan, Docker builds, and Trivy HIGH/CRITICAL image gates.
2. Publish immutable images to the existing ECR repositories using the commit SHA only after all gates pass.
3. Use a Jenkins-specific short-lived AWS role (OIDC/assume-role or an approved credential broker), not static access keys and not the developer's SSO session. Scope that role to the existing ECR, Terraform state, and deployment actions actually required.
4. Generate and archive a reviewed Terraform plan for `infrastructure/terraform/single-account`; require an explicit Jenkins approval before apply. Pass the immutable `image_tag` and preserve the current backend/state.
5. Deploy the frontend with `scripts/deploy-frontend.sh`, apply the API/worker image tag with Terraform, then run public frontend/API health checks and a fresh authenticated acceptance job.
6. Define rollback to a previous immutable image tag and frontend bundle without deleting S3/DynamoDB data. Test rollback in a safe environment before relying on it.
7. Run a real Jenkins pipeline and record build URL, commit, tool versions, scan outcomes, plan/apply result, smoke checks, and rollback procedure. Until then, Jenkins remains unverified.

Do not weaken secret or Trivy gates to make a build pass. Keep scanner details from exposing secret values in Jenkins logs. Add SonarQube or ZAP only with a configured server/scope and a blocking, reviewed policy; neither has a verified live result yet.

## Ansible implementation work

The stale k3s playbook and static-host inventory have been retired on `giri`. The replacement local-only `ci_workspace` role passed lint, syntax, initial check, apply, second apply, and final check on a disposable Docker target. It manages only agent workspace/config directories; no production build agent or cloud host has been provisioned or approved. See [the agent scope and commands](docs/ci-cd.md#agent-scope).

Terraform owns the deployed ECS/S3/DynamoDB/SQS/Cognito/ECR resources. Keep that ownership clear: Ansible must not independently create or mutate those same resources. The current app architecture has no long-lived EC2 application hosts, so first define Ansible's managed target with the project owner. A suitable scope is provisioning/configuring an explicitly approved Jenkins build agent; if the Jenkins agent is container-based, document why a Dockerfile is preferable and use Ansible only where it adds real value. Do not add an EC2 runner or other chargeable resources without approval.

For the approved scope, replace the static k3s examples with parameterized inventories/roles, use idempotent modules, avoid shell-based installers where supported modules exist, protect secrets with Ansible Vault or an external secret store, and add `ansible-lint`, `--syntax-check`, and `--check` validation. Test against a disposable agent first; document how it is provisioned, updated, and removed. Keep Docker as the only container runtime; do not install Podman.

## Git and handoff

- GitHub repository: <https://github.com/Girirraju/EchoScript>.
- Handover/deployment branch: `imran`.
- Last deployed-code commit before this documentation update: `f689f2f` (`Preserve workflow input after transcription`).
- At the last comparison, `imran` was 12 commits ahead of and 1 commit behind `main`. Review/merge through a pull request; do not force-push or rewrite history.
- The deployment changes are summarized in [docs/developer-handover-changes.md](docs/developer-handover-changes.md). Update this handover and [docs/implementation-status.md](docs/implementation-status.md) as acceptance checks pass.

## Release and completion criteria

The owner has accepted the working transcription path. Report AWS-hosted Jenkins and Ansible separately: hosting must be cost-approved before provisioning, Ansible must pass on a disposable AWS target before production configuration, and real AWS pipeline/plan/apply/smoke/rollback evidence is required before calling CI delivery operational. Include cost/budget approval, verified alert recipient, scan/test evidence and recovery instructions. The separate video/provider limitations remain outside the working transcription acceptance.
