# Architecture decisions

1. Horizontal navigation matches the enterprise reference and avoids an unnecessary sidebar.
2. Transcription and video states are independent so recap failure never invalidates a transcript.
3. Direct object-storage upload keeps large audio away from the synchronous API.
4. Repository and worker adapters allow local JSON/background processing and production S3/Kubernetes execution.
5. Blue/green colors are labels behind stable Services, enabling an atomic selector switch and quick rollback.
6. S3 metadata is acceptable for the demonstration but DynamoDB is the migration path for concurrency and listing scale.

## Current CI/CD decisions (giri, 2026-11-11)

The numbered decisions above describe the historical design; production now uses the single-account ECS/Fargate architecture documented in [deployment.md](deployment.md). Kubernetes selector switching and multi-account roots are not current deployment mechanisms.

- Separate untrusted PR validation from identity-bearing, reviewed release jobs. AWS-hosted Jenkins release agents use EC2 instance-profile credentials and short-lived `sts:AssumeRole` into five scoped job roles. PR/controller instance profiles cannot assume those application roles. Do not use GitHub Actions OIDC as Jenkins execution identity; the renderer emits permission policies only, while Terraform defines direct release-instance role trust. Never use developer SSO sessions or static AWS keys on Jenkins.
- Terraform exclusively owns AWS application resources. Routine release plans permit only the API, worker revision, workflow, and worker-policy updates; unrelated drift or data-resource changes fail closed. Archive encrypted saved plans because plaintext plans can contain sensitive state, and apply only after explicit named approval and checksum verification.
- Use the existing frontend S3/CloudFront mechanism with immutable release capsules and index-last publication. Preserve old hashed assets, user objects, S3 versions, and DynamoDB data; rollback uses existing images and the exact prior bundle through another approved plan.
- Bake tools into Docker. Restrict Ansible to a local agent workspace role tested on a disposable container; no application hosts exist to configure and no chargeable agent is implicitly approved.
- Maintain evidence separately from implementation. A local Jenkins run, mock rollback, owner-reported application success, and actual production plan/apply/smoke are distinct results. See [ci-verification.md](ci-verification.md).

