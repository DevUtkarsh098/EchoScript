# EchoScript handover guide

## Authority, scope, and evidence labels

The authoritative repository is [Girirraju/EchoScript](https://github.com/Girirraju/EchoScript), branch `main`. This review starts from commit `9164e5d7a7469aed500d8a1bb456b54d8c719f6e` and prepares changes on `codex/handover-security-gates`. The separate local recovery checkout remains a distinct source; its file-by-file reconciliation is recorded in `EchoScript-reconciliation-report.md`, `EchoScript-file-inventory.csv`, and `EchoScript-common-file-diff.patch` outside this clone. Do not merge it wholesale.

This guide uses **verified in source** for facts observed in this checkout, **historical evidence** for reports about a past environment, **unverified** for behavior requiring a live service, and **recommendation** for future work. Configuration and documentation describing an architecture are not proof that its runtime integration exists. The former AWS account, credentials, state, and running resources are unavailable for this handover; plan any future deployment for a new account and do not assume prior resources exist.

## Read this documentation

1. [README.md](README.md): purpose, repository entry points, quick setup.
2. [docs/architecture.md](docs/architecture.md): intended component architecture and trust boundaries; compare it with the implementation notes below.
3. [docs/implementation-status.md](docs/implementation-status.md): implementation claims and external verification list.
4. [docs/local-development.md](docs/local-development.md), [docs/api-contracts.md](docs/api-contracts.md), and [docs/decisions.md](docs/decisions.md): local workflow, API, and design decisions.
5. [docs/security.md](docs/security.md) and [docs/deployment.md](docs/deployment.md): controls and deployment guidance.

## Project purpose and source map

EchoScript is a web application for uploading audio, tracking transcription jobs, and obtaining transcript/subtitle outputs; it also contains a video recap/HeyGen integration boundary. The repository includes a React/TypeScript/Vite browser client, Python services, container and Kubernetes assets, Terraform/Ansible configuration, Jenkins pipelines, and monitoring configuration.

- `frontend/`: React/Vite SPA, browser routes, Cognito client integration, and API client.
- `services/ingest-service/app/`: FastAPI routes, Cognito JWT validation, job model and file-backed repository, local processing, health/metrics endpoints.
- `services/transcribe-worker/`: standalone faster-whisper/ffmpeg command-line worker.
- `services/video-service/`: separate FastAPI service, summary/provider adapter code.
- `shared/contracts/`: shared job contract material.
- `infrastructure/terraform/`: multiple account-oriented Terraform roots/modules; validate state/backend assumptions before using them.
- `infrastructure/ansible/`: host/bootstrap playbooks.
- `infrastructure/kubernetes/`: application manifests and job templates.
- `monitoring/`: Prometheus rules/configuration and Grafana assets. These are configuration assets, not proof of a complete deployed monitoring stack.
- `ci/`: Jenkins pipelines and CI scripts.

## Verified application behavior and gaps

### Frontend, authentication, and API

The frontend is a React/TypeScript/Vite single-page app. It has Cognito browser authentication configuration and calls the ingest API. The ingest API validates Cognito JWTs when mock mode is off. **Verified in source:** `mock_auth` defaults to enabled in the baseline. The baseline also defaulted `APP_ENV=local`, so a missing deployment setting could silently enable demo auth. This branch changes the `APP_ENV` default to `production` and rejects mock authentication unless `APP_ENV=local`, with regression tests. Local Compose and `.env.example` explicitly set local mode. Set `MOCK_AUTH=false` for all non-local deployments and verify Cognito configuration.

### Upload and transcription lifecycle

**Verified in source:** the API creates job metadata in `LocalJobRepository`, which stores JSON files; it returns an API upload URL `/api/uploads/{job_id}`. In the baseline, the authenticated upload handler looks up the hard-coded `demo-user-001` only in mock mode and otherwise has no owner lookup, so a normal authenticated upload is not a working end-to-end flow. Job start only runs the mock processor; when `MOCK_PROCESSING=false`, the route returns 503 because external Kubernetes orchestration is not implemented in the API. The mock path produces local outputs. The API does not invoke the faster-whisper worker.

`services/transcribe-worker` is a separate CLI accepting input/output and language arguments and produces transcript/subtitle output. **Unverified:** worker scheduling, durable job ownership, and output handoff are not connected to the API in this baseline. The documented S3 upload and DynamoDB persistence architecture is a target, not a verified source adapter: the inspected API repository has no S3 storage adapter or DynamoDB repository. Do not claim those integrations are functional until implemented and tested.

### Video service

The video service contains separate summary/HeyGen adapter code. The ingest route currently uses local mock video processing; end-to-end service invocation and provider behavior are unverified. Credentials, provider account, quotas, and actual rendering have not been verified.

## Infrastructure and delivery status

- **Docker:** Dockerfiles and Compose configuration exist. A successful current build is not established by this handover review.
- **Kubernetes/k3s:** application manifests and a worker Job template exist. The API does not create Jobs in the current source; cluster availability and deployed manifests are unverified.
- **Terraform/Ansible:** configuration and playbooks exist, but they are not applied or validated against a new account here. State boundaries, IAM permissions, networking, region, and resource inventory must be established before planning.
- **Jenkins:** three Jenkinsfiles exist. The delivery/runtime pipelines refer to absent scripts listed below. No Jenkins execution is verified.
- **SonarQube:** no SonarQube stage or tracked `sonar-project.properties` exists in this baseline. Server, token, and Quality Gate are unverified; local-only Sonar configuration was not recovered.
- **Trivy:** this branch adds filesystem secret scanning and HIGH+CRITICAL image gates to all three Jenkinsfiles. Scanner wrapper tests do not prove the Trivy binary accepted the options or scanned files. Trivy is unavailable in the review environment; see verification section.
- **OWASP ZAP:** no verified ZAP pipeline or live scan result is present in this baseline.
- **Monitoring:** Prometheus configuration/rules and Grafana dashboard/datasource files exist. The runtime Jenkinsfile points at a nonexistent `infrastructure/kubernetes/monitoring` path. A complete Alertmanager deployment/notification flow and protected dashboards are unverified.
- **Blue/green:** `ci/scripts/switch-color.sh` and `ci/scripts/rollback.sh` exist. Delivery also references missing `deploy-color.sh`. The switch script expects `SMOKE_URL` but the Jenkinsfile does not set it; its `.active-color` state is in the build workspace and is not durable. Do not treat the release/rollback process as ready.

### Missing or broken CI references

These are observed from the Jenkinsfiles and repository inventory:

| Pipeline reference | Status | Required behavior before enabling pipeline |
| --- | --- | --- |
| `ci/scripts/push-images.sh` | Missing | Authenticate to the intended ECR registry with scoped role credentials; push the exact immutable tags built and scanned; fail on any auth/push/tag mismatch. |
| `ci/scripts/deploy-color.sh` | Missing | Apply the selected inactive-color workload with the exact immutable image tag; wait for readiness; fail without changing the live Service. |
| `ci/scripts/switch-color.sh` | Exists, but `SMOKE_URL` is not supplied and state is workspace-local | Provide a validated smoke URL and durable active-color source; verify candidate before switching; record old color for reliable rollback. |
| `ci/scripts/rollback.sh` | Exists, but only toggles color via switch helper | Confirm current/last-good state and health semantics; avoid assuming a simple toggle is always a rollback. |
| `ci/scripts/switch-color.sh`, `rollback.sh`, `terraform-plan.sh` | Existing Git blobs have CRLF endings; WSL `bash -n` rejects them (including `switch-color.sh` and `rollback.sh`) | Normalize shell files to LF and validate with `bash -n` before relying on Linux Jenkins execution. This review did not alter those pre-existing scripts. |
| `infrastructure/kubernetes/monitoring` | Referenced path absent; files are under root `monitoring/` | Correct the deployment path and provide actual Prometheus/Grafana/Alertmanager Kubernetes resources before runtime pipeline use. |
| `ci/scripts/deploy-runtime.sh` | Missing | Publish worker/video images and apply/update runtime resources using immutable tags, scoped access, readiness checks, and failure handling. |
| `ci/scripts/terraform-apply.sh` | Missing | Only design after plan artifact integrity, backend/state locking, least-privilege role, approval binding, and plan identity are specified. It is intentionally not replaced in this handover. |
| SonarQube stage/config | Missing | Add only after server, project key, credentials binding, scanner, and blocking Quality Gate are defined. |
| ZAP scan stage/config | Missing | Define authenticated/unauthenticated target scope, safe test environment, baseline policy, and artifact handling before adding it. |

Existing `ci/scripts/terraform-plan.sh`, `ci/scripts/switch-color.sh`, `ci/scripts/rollback.sh`, and `scripts/smoke-test.sh` are present. Do not report them as missing.

## Security controls

- Keep Cognito verification enabled for non-local environments and enforce per-user ownership through job create, upload, status, and download operations.
- Do not put credentials in source, images, command-line arguments, test fixtures, logs, or reports. Use external secret stores/CI credentials.
- Keep administrative interfaces private; scope IAM and Kubernetes permissions to required resources/actions.
- This branch's image commands gate HIGH and CRITICAL findings and pass an explicit empty `--ignorefile=` setting so repository ignore files cannot suppress findings. This option still needs a real Trivy CLI compatibility check on the Jenkins agent.
- `ci/scripts/scan-secrets.sh` runs `trivy fs --scanners secret --secret-config ci/trivy-secret.yaml --ignorefile= --exit-code 1 --format table --quiet .`. The config disables Trivy's default Markdown allow rule. Scanner stdout/stderr is suppressed so matched content cannot enter Jenkins logs; the script reports a generic failure and preserves the exit status. Missing executable exits 127. Findings are not saved or archived, so detailed triage must run in a controlled local environment. Real scanner behavior remains unverified without the binary.
- Checkov IaC scanning is a separate control and does not replace secret or image scanning. Do not weaken gates to make a pipeline pass.

## Local development

Follow [docs/local-development.md](docs/local-development.md) and [README.md](README.md) for current prerequisites and commands. Typical entry points are `npm ci`/`npm run dev` under `frontend/` and the documented Python environment plus Uvicorn command under `services/ingest-service/`. Verify exact environment variables from the example/config docs; do not replace local environment files or use real credentials in mock mode. The backend tests use local test data; keep test artifacts isolated and do not reset user data. The worker requires its Python dependencies, ffmpeg, and model downloads; those requirements may make first startup resource-intensive.

## Historical evidence and current limitations

**Historical evidence from the separate recovery checkout, not verified against this clone or current AWS:** a November 2026 demo record described a temporary `t3.xlarge` in `us-east-1`, k3s, successful HIGH+CRITICAL scans of four images, blue/green switching/rollback, monitoring pods, and a public HTTPS endpoint. Later recorded AWS credentials were invalid and the endpoint timed out. Current account, instance, URL, and resource state are unknown. Treat the demo evidence as historical only; do not connect to, modify, or rely on those resources.

The GitHub baseline itself contains no proof of a current deployment. The former account is not a deployment target. A new-account plan must first establish account identity, region, quotas, DNS/certificates, network design, IAM, remote-state backend/locking, existing resources, budget, and cleanup schedule. Preserve S3/DynamoDB/Cognito only if the new account explicitly owns and authorizes those resources; do not assume cross-account access.

## Selectively recovered local changes

The recovery review selected only two small defensive changes for this branch: (1) ignore patterns for demo state, Terraform variable/plan files, pytest scratch, core dumps, and local blue/green state; and (2) a production-mode mock-auth guard with a focused regression test. Broader local changes to frontend upload auth, API storage, workers, Kubernetes, Terraform, Ansible, and deployment scripts were not copied because they are coupled, materially change behavior/infrastructure, or need isolated acceptance testing. They remain available in the untouched recovery checkout and reconciliation artifacts for separate review. Do not treat unreviewed local-only code as recovered.

## Prioritized next steps

1. Complete this branch review: validate actual Trivy CLI behavior on a supported Jenkins agent, add an authenticated upload/job acceptance path, and run existing tests/builds in a reproducible environment.
2. Design and test API-to-object-storage upload, DynamoDB metadata, worker Job creation, ownership checks, output persistence, and download flow together using a disposable test account/fixtures.
3. Complete Jenkins blockers above without weakening HIGH+CRITICAL or secret-scan gates; add Sonar only with an enforced Quality Gate.
4. Add and protect monitoring/Alertmanager resources, define safe ZAP scope, and test deployment, rollback, recovery, and cleanup.
5. For a new AWS account, review Terraform roots/state boundaries and Ansible tasks, prepare a non-mutating plan, inspect exact additions/updates/deletions and cost, then obtain explicit approval before any apply.

## This handover branch: verification state

Verification performed for this handover: `python3 -m unittest ci.tests.test_secret_scan -v` passed (4 tests); `bash -n ci/scripts/scan-secrets.sh` passed; Python AST parsing passed for the changed API/config/test files; `ci/trivy-secret.yaml` parsed with PyYAML; and `git diff --check` passed. The API test module could not run because FastAPI/Pytest dependencies are absent in this environment. `switch-color.sh`, `rollback.sh`, and `terraform-plan.sh` have CRLF line endings; Bash syntax checks fail in WSL, so normalize and validate before enabling these Linux Jenkins paths. Jenkins 2.580.1 is installed, but no connected Jenkins controller/Groovy pipeline linter was available. Trivy is unavailable, so run these on the Jenkins agent after installing the approved Trivy release and record `trivy --version`:

```sh
trivy --version
trivy fs --help
trivy image --help
bash ci/scripts/scan-secrets.sh
trivy image --ignorefile= --exit-code 1 --severity HIGH,CRITICAL gateway-ui:<IMAGE_TAG>
trivy image --ignorefile= --exit-code 1 --severity HIGH,CRITICAL ingest-service:<IMAGE_TAG>
trivy image --ignorefile= --exit-code 1 --severity HIGH,CRITICAL transcribe-worker:<IMAGE_TAG>
trivy image --ignorefile= --exit-code 1 --severity HIGH,CRITICAL video-service:<IMAGE_TAG>
```

Also verify Markdown coverage and exit behavior in a disposable workspace using a synthetic, non-credential test fixture; verify the nonzero result without displaying or retaining the fixture content. Never use a real credential for this test. Current Trivy documentation confirms `fs`/`--scanners secret`, `--secret-config`, empty `--ignorefile`, `--exit-code`, and HIGH/CRITICAL severities; Markdown's default allow rule is disabled with `disable-allow-rules: [markdown]`. That documentation review does not replace validating the CLI version installed on the Jenkins agent. Jenkins/Groovy pipeline validation, AWS deployment, real image scans, and a cloud release have not been run here. Record exact new evidence in [docs/implementation-status.md](docs/implementation-status.md); keep historical results labeled as such. Do not push this branch or modify `main` without separate approval.
