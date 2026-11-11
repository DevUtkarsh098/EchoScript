# Ansible scope

The historical k3s/static-host example was retired on `giri`. The active playbook configures a local, explicitly selected Docker build-agent workspace using the reusable `ci_workspace` role. It cannot target application servers or manage Terraform's AWS resources.

The AWS-only Jenkins proposal adds `playbooks/jenkins-hosts.yml`, `inventories/jenkins.aws_ec2.yml` and the reusable `jenkins_host` foundation role. It uses SSM and installs Docker/non-secret host configuration on approved Ubuntu hosts. The guard requires a disposable AWS test pass before production configuration. No AWS targets have been provisioned or tested; cost approval is required first. See [the AWS hosting proposal](../../docs/jenkins-aws-design.md). The old local workspace test remains a unit/disposable-container check and does not satisfy the AWS-host requirement.

Use the disposable image test documented in [the CI/CD runbook](../../docs/ci-cd.md). It exercises lint, syntax, check mode, apply, idempotence, and a final no-change check. No production agent or cloud infrastructure is provisioned. Changing inventories for a production agent requires approval of that specific target.
