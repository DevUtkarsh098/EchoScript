# Proposed AWS-only Jenkins hosting

This root has not been provisioned. Account and region are pinned to `598391748654` / `us-west-2`. The owner approved the proposed costs on 2026-11-11; reference `owner-chat-2026-11-11-cost-approved`. Review [the full cost/access design and scope](../../../docs/jenkins-aws-design.md) and reproduce costs with `python scripts/estimate-jenkins-cost.py` from the repository root.

Default approval values remain empty/zero; the provisioning preconditions reject them. Use the recorded approval reference and approved $220 account budget in the private provisioning inputs; do not invent a contact email. Pin a Canonical Ubuntu 24.04 amd64 AMI, verify own Identity Center profile `giri`, verify the alert contact and generate/review the five IAM policies from confirmed live application metadata before planning.

State ownership is separate: use the existing confirmed encrypted backend bucket and lock table but key **`echoscript/jenkins-hosting/terraform.tfstate`**. Never supply the application key `echoscript/prod/terraform.tfstate`. Do not bootstrap, migrate, import or replace existing state. Backend initialization and a live reviewed plan are still pending; only `init -backend=false` and validation have run.

The default agent state is stopped; disks continue to bill. Proposed root includes controller + isolated validation/release hosts, no public Jenkins/SSH ingress, a persistent encrypted 40 GiB controller disk, limited instance profiles/job roles, CI ECR repositories, empty machine secret containers, logs, SSM transfer scratch and Jenkins-volume-only backup selection. The disposable test host is disabled by default and must be tested before production Ansible configuration.

The host foundation role is prepared; controller/HTTPS/agent service units, job/agent authorization, certificate trust, secret bootstrap, logging and backup/restore acceptance still need implementation/test after cost/access approval. No application behavior or data is managed by this root. Do not run `terraform destroy`.
