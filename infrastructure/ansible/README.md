# Ansible scope

The historical k3s/static-host example was retired on `giri`. The active playbook configures a local, explicitly selected Docker build-agent workspace using the reusable `ci_workspace` role. It cannot target application servers or manage Terraform's AWS resources.

Use the disposable image test documented in [the CI/CD runbook](../../docs/ci-cd.md). It exercises lint, syntax, check mode, apply, idempotence, and a final no-change check. No production agent or cloud infrastructure is provisioned. Changing inventories for a production agent requires approval of that specific target.
