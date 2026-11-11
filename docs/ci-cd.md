# Jenkins delivery and Ansible agent configuration

Updated: 2026-11-11. Implementation branch: `giri`, created from `imran` at `c528ca0`. Preserve that ancestry; do not force-push. The project owner reports that transcription is working. This change does not alter the transcription implementation or migrate its data.

## Ownership and boundaries

Production remains account `598391748654`, region `us-west-2`, Terraform root `infrastructure/terraform/single-account`. CloudFront/private S3 serves the frontend; ECS Express Mode/Fargate serves the API and Fargate runs the worker. Terraform owns application infrastructure. Neither Jenkins shell scripts nor Ansible create a competing AWS resource model.

The account/region are enforced in the Terraform provider and release preflight. Backend bootstrap, state migration, `terraform destroy`, Kubernetes deployment, and data deletion are absent from the pipeline. The old infra/runtime Jenkins entrypoints now fail with retirement messages; the k3s playbook, static-host inventory, and selector-switch scripts were retired. Historical Terraform/Kubernetes directories remain for history and are not pipeline inputs.

## Agent scope

No production build agent or EC2 host has been approved or provisioned. `ci/agent/Dockerfile` installs the toolchain in a Docker image. Run agents on existing approved capacity, isolate each workspace and Docker daemon, and resolve/pin the tested image digest in the agent configuration. The image is a tool environment, not an inbound Jenkins connection by itself; the administrator must attach it using their approved Jenkins agent launcher.

Ansible has a deliberately narrow scope: `ci_workspace` creates an owned workspace/cache/config layout inside a selected local Docker agent. It installs only non-secret defaults. It does not install Docker, Jenkins, k3s, or AWS application resources. A Dockerfile owns tool installation; Ansible is useful only if this persistent workspace layout is wanted. If the chosen production agent is wholly ephemeral, keep the role as a disposable validation exercise and do not add an Ansible production deployment just to satisfy a checklist.

Build and test from the repository root:

```bash
docker build -f ci/agent/Dockerfile -t echoscript-ci-tools:local .
docker build -f ci/ansible-test.Dockerfile -t echoscript-ansible-test:local .
docker run --rm echoscript-ansible-test:local
```

The test image has no AWS files, SSH keys, Docker socket, or remote inventory. It runs `ansible-lint` with the production profile, syntax validation, initial check mode, apply, a second apply, and final check mode. The last two runs must show `changed=0`, `failed=0`, `unreachable=0`. Update role variables through a reviewed inventory for an explicitly approved local container. Only `/opt/...` workspace paths and local connections are allowed. `docker run --rm` removes the disposable target; no cloud cleanup is required. No secrets are managed by this role; future secret configuration must use an external store or Vault, never committed values.

## Jenkins job setup

Create two separate jobs, with Docker-only Linux agents:

1. A multibranch PR job using `ci/Jenkinsfile.validation`, label `echoscript-validation`. It must have no AWS identity, production token mounts, developer home directories, or production Docker daemon. Run untrusted PRs on disposable agents/daemons. A host Docker socket gives host-level authority and must not bridge this isolation boundary.
2. A restricted Pipeline-from-SCM release job using `ci/Jenkinsfile.delivery` from reviewed `giri`, label `echoscript-release`. Restrict job configuration, source approval, replay, build parameters, and approval permission to maintainers. Do not discover untrusted PR Jenkinsfiles on this identity-bearing agent. The job checks its source SHA against `origin/giri`. Keep this branch reviewed/protected before enabling deployment.

Required plugins: Pipeline (`workflow-aggregator`), Git, and their dependencies. No AWS credentials plugin, static key binding, SonarQube, or ZAP is needed. Those optional scanners have no verified configured server or blocking policy and were not added.

Validation executes frontend `npm ci`/build, API tests in its actual Docker image, worker tests in a disposable test layer over its actual image, fmt/validate of the active Terraform root with `init -backend=false -lockfile=readonly`, Ansible checks, source-secret scanning, and all three application Docker builds. Trivy gates API, worker, and frontend images at HIGH/CRITICAL without ignore rules or `--ignore-unfixed`. A scan or download error fails the build. Secret scanner stdout/stderr are suppressed on both clean and failing paths; regression tests verify this. Only vulnerability JSON (not secret findings) is archived.

Release `ACTION` defaults to `validate`; PR validation never publishes or deploys. `deploy` repeats all gates, publishes the exact scanned API/worker images under the full source commit SHA in the existing immutable ECR repositories, prepares the production frontend bundle, generates a saved plan against existing state, archives an encrypted plan plus a value-free summary, waits for named human approval, applies that exact saved plan, publishes the prepared frontend, and runs authenticated acceptance. Images are never rebuilt between their scan and push. Existing immutable tags cannot be overwritten; retries encountering a previously published tag fail rather than silently replacing it.

## Jenkins identity and configuration

Do not copy a developer's SSO session or configure static access keys. Each developer uses their own Identity Center assignment. The release job instead requires a Jenkins-specific OIDC issuer/approved credential broker which refreshes a short-lived JWT file outside the checkout. AWS CLI/SDK assumes each role through `AWS_WEB_IDENTITY_TOKEN_FILE`. No generic Jenkins OIDC issuer or trust has been assumed to exist.

An account administrator must approve and create the following roles and exact issuer/audience/subject trust. `ci/iam/render.py` renders reviewable JSON from confirmed live metadata; it does not call AWS or create infrastructure. Review the policies, attach appropriate organization boundaries, validate them with IAM Access Analyzer, and test actual read/plan/deploy permissions before describing them as operationally least privilege. Some AWS describe/register actions require `Resource: "*"`; they are action/region limited. The deploy role can update the workflow inline policy because the worker revision ARN changes; this permission requires particular review and strict source/job trust. No role has S3 DeleteObject, data-table writes, IAM role creation, or infrastructure deletion permissions.

| Jenkins administrator setting | Purpose |
| --- | --- |
| `JENKINS_PUBLISH_ROLE_ARN` | `arn:aws:iam::598391748654:role/echoscript-jenkins-publish`: ECR authorization and push to only the two existing repositories |
| `JENKINS_PLAN_ROLE_ARN` | `...:role/echoscript-jenkins-plan`: state/lock, resource reads, existing release-bundle reads |
| `JENKINS_DEPLOY_ROLE_ARN` | `...:role/echoscript-jenkins-deploy`: saved state writes, API update, worker task revision, workflow and its worker-policy update |
| `JENKINS_FRONTEND_ROLE_ARN` | `...:role/echoscript-jenkins-frontend`: state reads, frontend bucket reads/writes and exact distribution invalidation |
| `JENKINS_SMOKE_ROLE_ARN` | `...:role/echoscript-jenkins-smoke`: describe this workflow's execution only |
| `AWS_WEB_IDENTITY_TOKEN_FILE` | Externally supplied short-lived Jenkins JWT file, outside checkout; never log/archive it |
| `TF_BACKEND_FILE` | Read-only mounted existing credential-free `backend.hcl` with bucket/key/region/encrypt/lock-table literals |
| `TF_STATE_BUCKET`, `TF_STATE_KEY`, `TF_LOCK_TABLE` | Administrator-confirmed live backend metadata; must match the mounted file exactly |
| `TF_VAR_FILE` | Read-only mounted current production variable file; the pipeline overrides only `image_tag` |
| `TF_PLAN_RECIPIENT` | Operations' public `age` recipient; private decryption key stays outside Jenkins |
| `RELEASE_APPROVERS` | Named Jenkins users/group allowed to approve the exact saved plan |
| `SMOKE_TOKEN_FILE` | Externally refreshed short-lived Cognito access token for a dedicated test identity; not a developer token |
| `SMOKE_AUDIO_FILE` | Approved short English spoken WAV fixture under 5 MB, mounted outside source |
| `TOOLS_IMAGE` | Tested CI tooling image name/digest available on the isolated Docker daemon |

`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, and `AWS_PROFILE` are rejected by this chosen web-identity implementation. Shared credential/config files and instance metadata are disabled. The token broker must enforce audience, exact subject, trusted job, branch, and short expiry; Jenkins authorization alone cannot establish this trust. Do not put a role ARN, backend file, or token choice under PR control.

## Backend, plan protection, and approval

There is no configured live `backend.hcl` or initialized production backend in this checkout. The example and bootstrap code are historical evidence, not proof of the existing bucket/lock names. Obtain confirmed non-secret metadata from the account administrator; do not rerun bootstrap or infer that new state is wanted. CI requires that the state object already exists in the approved account/region before initializing. It uses only the existing default workspace, no `-migrate-state`, no `-reconfigure`, no state upload/import, and no provider lock updates.

The plan guard permits only in-place API changes, worker task revision replacement, transcription state-machine update, and its inline worker-revision policy update. Storage, IAM ownership changes, deletes, unrelated drift, and API replacement fail closed even before approval. Handle any broader infrastructure change through a separately reviewed administrative process; do not extend the allow list merely to make a release pass.

Saved plans can contain secrets even when terminal output redacts them. Therefore stdout/stderr and the plaintext plan remain in `ci-private` with restricted permissions; only an `age` encrypted saved plan, its SHA256, and a summary of addresses/actions are archived. Operations decrypts/reviews the complete plan through its approved secure process before approval. Apply verifies the saved-plan checksum. Jenkins artifact/workspace access must remain restricted, and `ci-private` is removed at build end. Review the documented [Terraform plan sensitivity](https://developer.hashicorp.com/terraform/cli/commands/plan) and [Jenkins input authorization](https://www.jenkins.io/doc/pipeline/steps/pipeline-input-step/) when configuring the controller.

## Acceptance and rollback

After apply, the pipeline waits for API health/readiness and `/version.commit` to match the requested image. It rejects unauthenticated jobs requests, creates a fresh authenticated WAV job, uploads without forwarding the bearer token to S3, completes the upload, starts transcription, and waits for both `TRANSCRIBED` and the same job-named Step Functions execution to be `SUCCEEDED`. It follows only approved regional S3 redirects for TXT/SRT/VTT and records nonempty-format checks, sizes and hashes. Logs/artifacts contain job ID and execution ARN, never token values, signed URLs, or transcript content. It does not delete the job or its outputs. Cross-user and failure-recovery acceptance remain separate exercises.

For a rollback, select release job `ACTION=rollback` and set `ROLLBACK_SHA` to a previous full 40-character image SHA with both ECR images and a previously archived frontend capsule. The pipeline still runs current security gates, verifies those existing images, retrieves `releases/<SHA>/frontend.tar.gz` and its checksum from the existing frontend bucket, plans with the previous `image_tag`, and requires a new explicit approval. It then applies that plan and restores the exact old bundle without rebuilding old source. Root hashed assets and unrelated S3 objects are preserved; `index.html` is published last and CloudFront invalidation is awaited. No `sync --delete` or data-table cleanup is used. Existing tags and retained bundles must remain available; a rollback can be blocked by a newly discovered vulnerability and must not bypass that gate.

Before the first automated production release, archive the current known-good frontend bundle under its actual deployed image SHA through an approved capture procedure. Do not manufacture a bundle from a newer checkout and label it as the deployed version. If no previous verified capsule exists, automated frontend rollback is not ready. There is no automatic rollback after partial Terraform failure: inspect state and service status, produce a fresh reviewed plan, and obtain approval.

`ci/tests/test_rollback.py` executes the real frontend restore script against local AWS/Terraform test doubles, verifies prior content and preservation of unrelated objects, and records a mock restore result. This proves script behavior, not a production rollback. A live rollback drill and authenticated smoke remain blocked until approved machine access, backend metadata, prior release capsule, and test identity are provided.

## Evidence and current limits

See [ci-verification.md](ci-verification.md) for actual tool versions, local Jenkins build URLs/commits, scan/test outcomes, and pending production steps. A locally successful Jenkins validation is not a production plan/apply or deployment success. Do not claim completion of live delivery until those separate results are recorded.
