# Implementation status

This status describes the GitHub `main` source at baseline commit `9164e5d7a7469aed500d8a1bb456b54d8c719f6e`, the handover changes, and the current deployment branch. Repository configuration is not proof of a running cloud deployment; live evidence is labeled below. See [HANDOFF_FOR_NEXT_DEVELOPER.md](../HANDOFF_FOR_NEXT_DEVELOPER.md) for architecture, source-verified gaps, and historical evidence.

## Present in source

- React/TypeScript/Vite frontend with Cognito browser integration.
- FastAPI ingest API, Cognito JWT validation code, file-backed local job repository, mock processing, health/version/metrics routes.
- Standalone faster-whisper worker CLI and separate video service/provider adapter code.
- Docker/Compose, Kubernetes manifests/job template, Terraform roots/modules, Ansible playbooks, Jenkinsfiles, Prometheus/Grafana configuration.
- CI scripts for Terraform plan, blue/green Service switch, rollback helper, and smoke test.

## Baseline limitations (before this deployment branch)

- Authenticated upload does not resolve a user's job record in the baseline handler; normal authenticated upload therefore cannot complete.
- API job start only supports mock processing. It does not create Kubernetes Jobs or invoke the standalone faster-whisper worker.
- The baseline API source had no S3 storage adapter or DynamoDB repository. Deployment-branch adapters now exist; integrated AWS behavior is still unverified.
- Video service end-to-end invocation/provider behavior is not verified.
- Jenkins references missing scripts and a missing monitoring path; see the handover blocker table.
- No tracked SonarQube stage/configuration or verified Quality Gate, OWASP ZAP pipeline/result, or complete monitoring/Alertmanager stack is established.

## Handover branch changes and verification

- Trivy image commands now gate HIGH and CRITICAL findings and pass an explicit empty ignore-file setting.
- Delivery, runtime, and infrastructure pipelines run a Trivy filesystem secret scan. Its configuration disables the default Markdown allow rule; scanner output is suppressed from CI logs; the wrapper fails on findings, missing scanner, or scanner errors.
- `.gitignore` now excludes demo state, Terraform variable/plan files, temporary test output, core dumps, and local blue/green state.
- Mock authentication now fails closed by default: `APP_ENV` defaults to `production`, and mock auth is rejected unless `APP_ENV=local`. Local Compose/example settings explicitly choose local mode; regression tests cover the guard.
- Wrapper tests and shell syntax checks are run for this handover. Trivy is unavailable here; no real scan, Jenkins execution, image build/scan, AWS plan/apply, or cloud release has been performed.

## Deployment branch implementation and verification

- Frontend mock authentication now fails closed unless both `VITE_APP_ENV=local` and `VITE_MOCK_AUTH=true` are explicitly set. Cognito client configuration is passed through the frontend image build arguments; local Compose selects local demo mode explicitly.
- Audio upload requests now carry the in-memory Cognito access token. The API resolves the job under the authenticated principal, checks the declared media type and size, and streams uploads through a temporary file before atomically moving them into place. Transcript, subtitle, audio, and video reads now use the authenticated API client. A regression test covers cross-user upload rejection.
- Terraform defaults and image references target `us-west-2`. The single-account root now defines CloudFront/private S3, Cognito, ECS Express Mode, DynamoDB, SQS/DLQ, Lambda/Step Functions, Fargate, scoped IAM roles, and budget resources.
- API source now has S3/DynamoDB/SQS adapters, authenticated ownership-scoped presigned uploads/downloads, verified upload completion, queue dispatch, and worker-side faster-whisper processing with TXT/SRT/VTT persistence. Adapter and API regression tests are present. The cloud workflow has not yet been exercised against AWS.
- Deployment scripts verify that the active AWS account and region match Terraform outputs before image publication or frontend deployment. The publish script invokes the secret scan through Bash so it works with the checked-out file mode.
- On 2026-11-11, Docker built the API and worker images for Linux AMD64 using pinned Amazon Linux 2023 release `2023.12.20261109`. Trivy source-secret scanning passed; both images passed the HIGH/CRITICAL vulnerability gate with zero findings. Immutable tag `81092db` was pushed to ECR in account `598391748654`, region `us-west-2`.
- Terraform validation passed. The reviewed plan showed 75 additions, 0 changes, and 0 deletions; apply completed with 75 resources added. The deployed frontend returned HTTP 200. The ECS API task and ALB target are healthy, and `/ready` returned `200` through the active ALB.
- The frontend production build completed and the assets were synced to the private S3 bucket; CloudFront invalidation was requested. The `$100/month` AWS Budget has no email notification recipient configured.

## External verification still required

- Run the exact secret and image scan commands with the approved Trivy release on the Jenkins agent; confirm ignore-file syntax and Markdown coverage with a harmless fixture, without committing or printing credentials.
- Complete authenticated acceptance with a real user: Cognito sign-in, owner-isolation/cross-user rejection, real audio upload, worker transcription, durable persistence, TXT/SRT/VTT downloads, and failure/retry behavior.
- Review the AWS bill and configure budget email notifications if wanted; the `$85–$110/month` planning range is not a cost cap.
- Configure Jenkins credentials outside source, restore missing pipeline scripts/path, enforce Sonar Quality Gate if adopted, define ZAP scope, and validate private monitoring/alert delivery.

The active AWS account and resources are recorded in [docs/deployment.md](deployment.md). Core services are provisioned and live; end-to-end authenticated audio acceptance remains outstanding.
