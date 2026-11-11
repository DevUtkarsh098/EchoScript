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
- Jenkins: repository files exist but are stale, reference missing scripts, and target Kubernetes/old account layouts. No working Jenkins deployment pipeline or run has been verified.
- Ansible: sample playbooks exist but install k3s on static example hosts. They are not suitable for the deployed ECS architecture and have not been verified.
- SonarQube quality gate, OWASP ZAP scan, complete monitoring/alert delivery, and production rollback exercise.
- Actual AWS billing review and budget email alert. A `$100/month` budget exists without an email; current estimate is `$85–$110/month`.
- Video/provider workflow acceptance.

## Next implementation priorities

1. Complete the fresh authenticated transcription and output-download acceptance listed in the handover.
2. Redesign Jenkins around the existing single-account Terraform root, immutable ECR tags, short-lived scoped AWS access, an approval-gated plan/apply, smoke checks, and rollback.
3. Decide and document Ansible's target. The deployed application has no long-lived EC2 hosts; do not provision chargeable agents without approval. Remove/retire stale k3s examples from the production path.
4. Verify access isolation and failure recovery, then reconcile billing, alerting, FFmpeg expectations, and the separate video scope.
