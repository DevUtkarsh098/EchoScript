# CI/CD verification evidence

Date: 2026-11-11. Branch `giri`, based on `imran` commit `c528ca0`. This record separates implemented controls, actual local tests, and unexecuted production work. The owner reports the existing transcription path is working; this task does not reclassify that owner test as a Jenkins smoke test.

## Completed local checks

- Docker Desktop engine 29.9.2 started; no cloud infrastructure provisioned.
- CI tooling Docker image built from `ci/agent/Dockerfile`.
- Ansible core 2.19.3, ansible-lint 25.9.2 production profile: lint and syntax passed. Initial check/apply each proposed/made two task changes. Second apply and final check both reported `ok=3 changed=0 unreachable=0 failed=0` on a disposable local Docker target.
- Eleven CI regression tests passed in Docker: source-secret scanner success/finding/error/missing behavior with output suppression; backend metadata validation; release-plan allow list and data-change rejection; safe bundle extraction; actual frontend rollback script with local AWS/Terraform doubles. The rollback test restored the exact prior bundle and preserved an unrelated object.
- Terraform formatting check passed for `single-account`. The first Linux validate attempt exposed a missing platform checksum in the existing lock file; verified checksums for the same locked provider versions are being added, without provider upgrades or backend access.

## Jenkins, builds, and scans

A disposable local Jenkins controller is being prepared to run `ci/Jenkinsfile.validation` from the committed `giri` source. Record the build URL, exact tested SHA, tool versions, stages, and vulnerability results here after the run. A local validation job has no AWS credentials/backend/test-user mounts and cannot deploy production.

## Production work not executed

- No approved production Jenkins controller/job, agent, OIDC issuer/broker, or role trust was supplied.
- No confirmed existing backend bucket/lock metadata or mounted production variables were supplied. No production `terraform init`, plan, or apply was executed.
- No CI test-user token source, approved spoken-audio fixture, or known-good frontend release capsule was supplied. No production authenticated CI smoke job or live rollback was executed.
- IAM policy JSON generation is a review aid, not evidence of installed permissions or successful role assumption. IAM Access Analyzer and real plan/apply authorization remain required.

Do not report production Jenkins delivery as complete until those items are configured and a real approval-gated plan/apply, smoke and rollback drill have evidence. See [ci-cd.md](ci-cd.md) for the concrete setup and procedure.
