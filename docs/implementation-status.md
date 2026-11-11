# Implementation status

Updated: 2026-11-11. This page distinguishes code present in the repository from behavior verified in the deployed AWS environment. See [the developer handover](../HANDOFF_FOR_NEXT_DEVELOPER.md) for takeover instructions and acceptance criteria.

## Implemented and verified

- React/TypeScript frontend with Cognito sign-in; sign-in was completed in the browser.
- Authenticated audio upload to private S3 using regional us-west-2 signing and configured S3 CORS.
- FastAPI ingest API with Cognito JWT validation and owner-scoped job access.
- DynamoDB job records, SQS/Lambda/Step Functions orchestration, and Fargate faster-whisper worker.
- Synthetic audio was transcribed. TXT, SRT, and VTT output objects were written to S3 and the job status became `TRANSCRIBED`.
- Fixed workflow input preservation after the worker task. A retry of the already-transcribed job completed, but that retry skipped inference; a fresh end-to-end success is still needed.
- AWS application resources are provisioned in account `598391748654`, region `us-west-2`, using `infrastructure/terraform/single-account`.
- Docker image publishing gates were run: Trivy source secret scan passed and published API/worker images had zero HIGH/CRITICAL findings. API health returned `{"status":"ok"}`.

## Not yet accepted or verified

- A fresh job whose same Step Functions execution performs transcription and ends `SUCCEEDED`.
- Download and content inspection of TXT/SRT/VTT in the authenticated web UI.
- Cross-user and unauthenticated access denial, worker failure/retry/recovery, and representative real-speech quality.
- Whether PyAV decoding satisfies the original handover's separate FFmpeg requirement; the deployed worker uses PyAV and does not install a separate FFmpeg executable.
- Production Jenkins delivery: the `giri` implementation replaces stale Kubernetes/account layouts with current-architecture validation and approval-gated immutable releases. Actual local verification is in [ci-verification.md](ci-verification.md); AWS identity/backend configuration, production plan/apply, authenticated CI smoke, and a live rollback remain pending.
- Production Ansible target: the local-only agent workspace role passed lint, syntax, check, apply and idempotence in Docker. No production agent was approved/provisioned; Ansible does not manage ECS or any Terraform-owned AWS resources. The k3s/static-host examples were retired.
- SonarQube quality gate, OWASP ZAP scan, complete monitoring/alert delivery, and production rollback exercise.
- Actual AWS billing review and budget email alert. A `$100/month` budget exists without an email; current estimate is `$85–$110/month`.
- Video/provider workflow acceptance.

## Next implementation priorities

1. Complete the fresh authenticated transcription and output-download acceptance listed in the handover.
2. Configure approved Jenkins jobs/agents, exact OIDC trust and scoped roles, confirmed existing backend metadata, protected plan decryption/approval, and an external test identity. Run and record real production release/rollback results using [ci-cd.md](ci-cd.md).
3. Decide whether the approved production agent benefits from the tested Ansible workspace role; otherwise keep its toolchain in the Dockerfile. Do not provision chargeable agents without approval.
4. Verify access isolation and failure recovery, then reconcile billing, alerting, FFmpeg expectations, and the separate video scope.
