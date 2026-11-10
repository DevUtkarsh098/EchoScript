# Implementation status

This status describes the GitHub `main` source at baseline commit `9164e5d7a7469aed500d8a1bb456b54d8c719f6e`, plus clearly labeled changes on `codex/handover-security-gates`. Repository configuration is not proof of a running cloud deployment. See [HANDOFF_FOR_NEXT_DEVELOPER.md](../HANDOFF_FOR_NEXT_DEVELOPER.md) for architecture, source-verified gaps, historical evidence, and prioritized work.

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
- No tracked SonarQube stage/configuration or verified Quality Gate, OWASP ZAP pipeline/result, complete deployed monitoring/Alertmanager stack, or current cloud deployment is established.

## Handover branch changes and verification

- Trivy image commands now gate HIGH and CRITICAL findings and pass an explicit empty ignore-file setting.
- Delivery, runtime, and infrastructure pipelines run a Trivy filesystem secret scan. Its configuration disables the default Markdown allow rule; scanner output is suppressed from CI logs; the wrapper fails on findings, missing scanner, or scanner errors.
- `.gitignore` now excludes demo state, Terraform variable/plan files, temporary test output, core dumps, and local blue/green state.
- Mock authentication now fails closed by default: `APP_ENV` defaults to `production`, and mock auth is rejected unless `APP_ENV=local`. Local Compose/example settings explicitly choose local mode; regression tests cover the guard.
- Wrapper tests and shell syntax checks are run for this handover. Trivy is unavailable here; no real scan, Jenkins execution, image build/scan, AWS plan/apply, or cloud release has been performed.

## Deployment branch implementation and verification

- Frontend mock authentication now fails closed unless both `VITE_APP_ENV=local` and `VITE_MOCK_AUTH=true` are explicitly set. Cognito client configuration is passed through the frontend image build arguments; local Compose selects local demo mode explicitly.
- Audio upload requests now carry the in-memory Cognito access token. The API resolves the job under the authenticated principal, checks the declared media type and size, and streams uploads through a temporary file before atomically moving them into place. Transcript, subtitle, audio, and video reads now use the authenticated API client. A regression test covers cross-user upload rejection.
- Terraform defaults and image references target `us-west-2`. A single-account root defines CloudFront/private S3, Cognito, App Runner, DynamoDB, SQS/DLQ, Lambda/Step Functions, Fargate, scoped IAM roles, and budget resources. No AWS identity check or infrastructure action has been performed.
- API source now has S3/DynamoDB/SQS adapters, authenticated ownership-scoped presigned uploads/downloads, verified upload completion, queue dispatch, and worker-side faster-whisper processing with TXT/SRT/VTT persistence. Adapter and API regression tests are present. The cloud workflow has not yet been exercised against AWS.
- Deployment scripts verify that the active AWS account and region match Terraform outputs before image publication or frontend deployment. The infrastructure-to-image bootstrapping sequence is documented. No images or frontend assets have been published.
- Frontend production build passes; frontend auth guard tests (3), backend pytest (10), Ruff lint, and secret-scan wrapper tests (4) pass. Compose configuration parses, Python source compiles, shell scripts parse, Terraform formatting and validation pass, and `git diff --check` passes. Trivy and a usable Docker daemon are unavailable. No live AWS tests, actual image scans, or image builds have run. Existing `npm audit` reported 15 dependency advisories (10 moderate, 3 high, 2 critical); no automatic upgrades were applied.
- AWS account credentials are not configured, as confirmed by the owner. No AWS API has been called and no infrastructure has been created. The architecture and planning range are approved; chargeable resource creation still requires separate explicit approval.

## External verification still required

- Run the exact secret and image scan commands with the approved Trivy release on the Jenkins agent; confirm ignore-file syntax and Markdown coverage with a harmless fixture, without committing or printing credentials.
- Run backend/frontend checks in a reproducible environment and exercise Cognito, owner isolation, upload, worker execution, durable persistence, output download, and failure/retry behavior.
- Inspect a new AWS account, state backend, networking, IAM, quotas, region, budget, and cleanup plan before preparing a non-mutating Terraform plan.
- Configure Jenkins credentials outside source, restore missing pipeline scripts/path, enforce Sonar Quality Gate if adopted, define ZAP scope, and validate private monitoring/alert delivery.

No current AWS account/resource access is assumed. No infrastructure was provisioned or changed for this handover.
