# Disposable local Jenkins verification

**Retired by the AWS-only hosting requirement on 2026-11-11.** The former local controller was stopped and its Dockerfile/initializer removed. The procedure below is historical context only; do not run it. Laptop runs do not satisfy AWS-hosted Jenkins or disposable AWS-host acceptance. Use [the cost-gated AWS design](../../docs/jenkins-aws-design.md).

This is a local-only validation controller, not a production installation. It combines a controller and tools solely to inspect the pipeline on an existing developer machine. It binds only `127.0.0.1:8088`, disables signup/anonymous access, and creates a random local test administrator. It has no AWS credentials or production configuration.

From a fresh checkout, build `ci/agent/Dockerfile` first, then `docker build -f ci/local/Dockerfile -t echoscript-jenkins-local .`. Create a committed-source-only bare clone under ignored `.local-run/jenkins-source.git` (`git clone --bare . .local-run/jenkins-source.git`). Generate a random 32-byte password into ignored `.local-run/jenkins-password` without printing or committing it. The initializer uses username `local-ci` and reads the mounted password file.

Start Docker with these mounts (replace `ABSOLUTE_REPO` with the repository's actual absolute path):

```bash
docker run -d --name echoscript-jenkins-local -p 127.0.0.1:8088:8080 \
  -v ABSOLUTE_REPO/.local-run/jenkins-source.git:/source:ro \
  -v ABSOLUTE_REPO/.local-run/jenkins-password:/run/secrets/local_password:ro \
  -v echoscript-jenkins-local-home:/var/jenkins_home \
  echoscript-jenkins-local
```

The job is created at <http://localhost:8088/job/echoscript-validation/>. The default controller intentionally has no Docker daemon access, so validation can execute source/frontend/Terraform checks but stops when image builds are reached. Do not call that a successful full pipeline. Use an approved isolated Docker agent for the full run. Mounting the host Docker socket grants host-level container authority and requires explicit approval; automatic review rejected that mount in this session.

For updates, finish/stop any build, fast-forward the local bare copy from `giri`, rebuild tools/controller if changed, and replace only this named local container while retaining its test volume. The production job must instead use separate reviewed source, isolated agents, HTTPS/authenticated Jenkins, and approved machine identity as described in [the runbook](../../docs/ci-cd.md).

Cleanup: stop and remove only `echoscript-jenkins-local` after exporting the required evidence. Retain `echoscript-jenkins-local-home` while build links/history are needed; remove that specifically named test volume only when its local evidence is no longer wanted. No AWS cleanup or application data deletion is involved.
