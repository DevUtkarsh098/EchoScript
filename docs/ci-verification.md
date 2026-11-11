# CI/CD verification evidence

Date: 2026-11-11. Branch `giri`, based on `imran` commit `c528ca0`. This record separates implemented controls, actual local tests, and unexecuted production work. The owner reports the existing transcription path is working; this task does not reclassify that owner test as a Jenkins smoke test.

## AWS-only hosting update

The latest user instructions require AWS-hosted Jenkins and a disposable **AWS** Ansible target after cost approval. The laptop controller was stopped and its launch files retired. Historical localhost links below are retained as evidence, not current hosting or acceptance.

Prepared [the costed AWS design](jenkins-aws-design.md), proposed `jenkins-hosting` Terraform root, SSM inventory and guarded host foundation role. Added fixed 15-minute EC2 machine-role profiles with tests rejecting developer/static-key profiles. Backend-free Terraform validation passed, Ansible lint/syntax passed with `amazon.aws` 10.3.2, and 18 CI safety tests passed. No AWS backend was initialized and no hosting plan/apply or AWS target check/apply test was executed. Own profile `giri` and the account contact email remain to be verified after approval; no other developer's credentials were read or reused.

Requested approval is **$70–$85/month extra**, **$220 account budget with verified contact alerts**, and **$2 one-off AWS test allowance**. Approval has not been granted. Do not interpret an instruction to choose sensible defaults as approval of these costs.

Exact follow-up source commit `80930d1886f1d60b719538a9c4bce27ebbcc6746` was exported using `git archive` and tested in a disposable tools container, excluding local credentials/private artifacts. The real Trivy source-secret scan passed, all 18 safety tests passed, the cost script reproduced $69.47 nominal/$70–$85 planned, and Ansible lint/syntax passed. No Jenkins service or AWS target was started for those checks. Documentation-only commits after this source snapshot record evidence rather than imply a new AWS pipeline run.

## Completed local checks

- Docker Desktop engine 29.9.2 started; no cloud infrastructure provisioned.
- CI tooling Docker image built from `ci/agent/Dockerfile`.
- Ansible core 2.19.3, ansible-lint 25.9.2 production profile: lint and syntax passed. Initial check/apply each proposed/made two task changes. Second apply and final check both reported `ok=3 changed=0 unreachable=0 failed=0` on a disposable local Docker target.
- Fifteen CI regression tests passed in Docker: source-secret scanner success/finding/error/missing behavior with output suppression; backend metadata validation; release-plan allow list and data-change rejection; safe bundle extraction; actual frontend rollback script with local AWS/Terraform doubles; IAM permission scope; and real age encryption/decryption of private diagnostics. The rollback test restored the exact prior bundle and preserved an unrelated object.
- Terraform fmt and validate passed for `single-account`, using `init -backend=false -lockfile=readonly`. The first Linux attempt exposed a missing platform checksum in the existing lock file. `terraform providers lock -platform=linux_amd64 -platform=windows_amd64` added HashiCorp-signed checksums for the SAME versions (AWS 6.72.0, archive 2.8.1). No provider upgrade or production backend access occurred.
- Ten API tests passed inside the clean API image. Two worker tests passed in a disposable layer over the clean worker image, including actual faster-whisper imports and PyAV decoding of a generated PCM WAV without downloading a model. These are not production inference tests.
- Frontend Docker production build passed with `npm ci`; all three existing auth configuration tests passed with Vite 8.3.8/Vitest 5.1.0. `nginx -t` passed on the final frontend image. `npm audit --audit-level=high` passed with zero high/critical findings; seven moderate development-tool advisories remain reported.
- Release/shared Jenkins Groovy scripts were compile-checked inside the real local Jenkins controller without executing release stages. Shell syntax checks passed for all CI/deployment scripts.

## Jenkins, builds, and scans

A real password-protected local Jenkins 2.580.2 controller ran [validation build #1](http://localhost:8088/job/echoscript-validation/1/) from source commit `a047a4d725ec13f00f8c2cdb6241398799d475d5`. Tool versions, the source commit and stage output are archived there. Source-secret scanning, all 11 CI tests present at that commit, frontend production build, Terraform fmt and validation passed. The run then ended **FAILURE at the API image stage** because no Docker daemon/socket was provided. Later working-tree checks added IAM/encryption/decoder tests and dependency remediation, as recorded above; those are separate evidence from build #1.

The final committed implementation was rerun in [validation build #2](http://localhost:8088/job/echoscript-validation/2/) at commit `c6700974f547bd22b1fb9e0cf763f3016af67da9`. Its actual Jenkins stage statuses were:

| Stage | Result |
| --- | --- |
| Tool versions (including Buildx) | SUCCESS |
| Secret scan and all 15 CI regression tests | SUCCESS |
| Frontend production build, 3 auth tests, HIGH/CRITICAL npm audit gate | SUCCESS |
| Terraform fmt / backend-free init / validate | SUCCESS |
| API image and tests | FAILED: Docker daemon unavailable |
| Remaining worker/Ansible/image scan stages | Not reached in Jenkins; independent evidence is listed above |

Build #2 therefore ended **FAILURE**, not a successful full pipeline. Tool versions and `npm-audit.json` are archived in that build. The exact final Ansible test image was also built/run independently with the final tooling image; lint/syntax/check/apply/idempotence all passed again. `imran` remains an ancestor of `giri`; no history was rewritten. Documentation-only evidence commits after this tested implementation do not imply another completed Jenkins run.

Automatic approval review rejected the attempted host Docker socket mount because it grants Jenkins broad host-level container authority. The controller was instead started without that mount, AWS credentials, backend files, or a smoke identity. This was not bypassed. The later AWS-only requirement supersedes the local socket option: full delivery needs approved AWS-hosted agents. Independent image checks below used direct Docker commands and exported image archives; scanners had no Docker socket.

| Tool | Tested version |
| --- | --- |
| Jenkins / Java | 2.580.2 / 21.0.13+9 |
| Git | 2.39.5 |
| Docker engine / CI client / Buildx | 29.9.2 / 29.0.0 / 0.29.1 |
| Node / npm | 22.23.4 / 10.9.9 |
| Python | 3.12.16 |
| Terraform / locked providers | 1.14.0 / AWS 6.72.0, archive 2.8.1 |
| AWS CLI | 2.31.26 |
| Trivy | 0.76.2 |
| Ansible core / ansible-lint | 2.19.3 / 25.9.2 |
| Vite / Vitest / Nginx runtime | 8.3.8 / 5.1.0 / 1.30.6 |

### Security-gate results

The initial frontend runtime failed with **66 HIGH / 3 CRITICAL** findings. Its old Nginx/OS packages were updated; no ignore rules were added. The initial frontend dependency graph failed with **2 HIGH / 3 CRITICAL** findings. Fixed build/test tooling and removal of the unused form/validation dependency set resolved the requested severity gates. API, worker, and transcription implementation code was preserved.

Final independent Trivy results, all **0 HIGH / 0 CRITICAL**:

| Local report | SHA256 |
| --- | --- |
| `ci-artifacts/trivy-api-local.json` | `281164b85c03bc35e1263a20a0a6b29e00337a3bbd9f3329af8cc46be97e5a22` |
| `ci-artifacts/trivy-worker-local.json` | `27d4f47f6524eb7184ef16d81633da752c60fd42a0a10d25407109e36ac9f944` |
| `ci-artifacts/trivy-frontend-final.json` | `e0801a0b2bcaf03f750ae788a8dce639d9cfeb49ce5ec7a45dfbb0fa4c28fd2b` |
| `ci-artifacts/trivy-frontend-dependencies-patched.json` | `3db2b564f28f2eedc668bfda5573b44cca5fb446f6ff669982a71e1630c77de9` |

Local image IDs (test tags `:ci-check`, NOT published release attestations):

- API: `sha256:ec5064c03753ded445c27a10f1871d4f995a0daba5b9655aa330f1cadad23ef1`.
- Worker: `sha256:9a5ffe1852eda6930ac1364677728fab63f5b4fe2c5204a29865016f618ddbd9`.
- Frontend: `sha256:807c0df83732b2487c1506b42036e4b4c1138d062d56373b5acc13b6ced1a3f3`.

### Read-only production checks

On 2026-11-11 the public frontend returned HTTP 200, `/health` returned HTTP 200 with `{"status":"ok"}`, `/ready` returned HTTP 200 with `{"status":"ready"}`, and `/version` returned `version=0.1.0`, `commit=277a786`, `color=single`. These observations did not authenticate, submit jobs, or modify production. They do not prove the running image was built from the latest handover commit and do not replace authenticated CI acceptance.

## Production work not executed

- No approved production Jenkins controller/job, agent, OIDC issuer/broker, or role trust was supplied.
- No confirmed existing backend bucket/lock metadata or mounted production variables were supplied. No production `terraform init`, plan, or apply was executed.
- No CI test-user token source, approved spoken-audio fixture, or known-good frontend release capsule was supplied. No production authenticated CI smoke job or live rollback was executed.
- IAM policy JSON generation is a review aid, not evidence of installed permissions or successful role assumption. IAM Access Analyzer and real plan/apply authorization remain required.

Do not report production Jenkins delivery as complete until those items are configured and a real approval-gated plan/apply, smoke and rollback drill have evidence. See [ci-cd.md](ci-cd.md) for the concrete setup and procedure.
