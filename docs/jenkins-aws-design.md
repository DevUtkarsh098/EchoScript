# AWS Jenkins hosting design — cost approved

Date: 2026-11-11. Branch: `giri`. Status: design/configuration prepared; **no AWS Jenkins resources have been provisioned**. The owner's transcription workflow is working and remains unchanged.

The owner approved the proposed costs on 2026-11-11 with “cost approved do that”. Reference: `owner-chat-2026-11-11-cost-approved`. This covers $70–$85/month additional Jenkins hosting with agents stopped when idle, a $220/month account-wide budget with verified contact alerts, and the $2 one-off disposable AWS test. Cost approval is no longer pending. Provisioning still requires the developer's own authenticated AWS access, confirmed backend/contact/AMI/policies and a reviewed plan within this scope.

The latest supplied instructions require Jenkins in account `598391748654`, region `us-west-2`, prohibit laptop/external hosting, and require cost approval before chargeable provisioning. The earlier local Jenkins container was stopped and its launch files retired. Its old build records are historical implementation tests, not AWS completion evidence.

## Proposed resources and ownership

Terraform proposal: `infrastructure/terraform/jenkins-hosting`. It owns only new CI infrastructure: a dedicated VPC/subnet, three distinct security groups and EC2 hosts, IAM instance profiles and five job roles, encrypted disks, an SSM transfer bucket, CI image repositories, empty Secrets Manager bootstrap containers, logs and backup configuration.

| Host | Size / disk | Intended use |
| --- | --- | --- |
| Controller | t3a.medium, 2 vCPU / 4 GiB; 20 GiB root + separate encrypted 40 GiB data | Persistent Jenkins, zero build executors, no Docker socket exposed to Jenkins |
| Validation | t3a.large, 2 vCPU / 8 GiB; encrypted 100 GiB root | Untrusted PR checks, isolated Docker daemon, no application deployment role |
| Release | t3a.large, 2 vCPU / 8 GiB; encrypted 100 GiB root | Reviewed delivery job, separate daemon and scoped short-lived role assumption |
| Disposable test (optional) | t3a.large, encrypted 100 GiB | First Ansible AWS test only, before production host configuration; disabled by default |

Agents default to **stopped** after provisioning. The estimate assumes starting validation for 100 hours/month and release for 20 hours/month, then stopping them after work. EBS continues billing while stopped. Start/stop must be coordinated with builds; the Terraform `agent_desired_state` setting must not be applied during an active build. T3a credit mode is `standard`, avoiding unlimited-credit surcharges but permitting throttling when credits are depleted. One executor per agent; measure CPU/memory/disk during the AWS pilot.

The application's active root stays `infrastructure/terraform/single-account`. Its ECS/Fargate/S3/DynamoDB/Cognito/ECR resources stay there. Hosting uses the **same confirmed existing encrypted state bucket and lock table**, with a new isolated key `echoscript/jenkins-hosting/terraform.tfstate`; the application's existing `echoscript/prod/terraform.tfstate` object is not replaced, imported, migrated, or reused for different resources. No bootstrap root is rerun. Never run `terraform destroy`.

The proposal's preconditions reject provisioning without an explicit cost/access approval reference, approved account budget and verified alert email, and all five reviewed role policies. They are guardrails, not proof of human approval; do not fill them speculatively. Existing bucket/lock names, pinned Ubuntu AMI, actual IAM policy metadata and alert email still require verification through the developer's own access.

## Monthly cost and budget impact

USD, on-demand Linux, 730-hour controller month, no reservation/Spot commitment, before tax. The two EC2 rates were read directly from [AWS's public Oregon price feed](https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel/US%20West%20(Oregon)/Linux/index.json), publication `2026-11-10T17:38:52Z`: t3a.medium **$0.0376/hour**, t3a.large **$0.0752/hour**. Rate codes: `K7FNMEK8WF6ZAS8V.JRTCKXETXF.6YS6EN2CT7` and `GH8WPQ59336X6S8E.JRTCKXETXF.6YS6EN2CT7`.

| Component | Planning arithmetic / assumption | Monthly |
| --- | --- | ---: |
| Controller compute | 730 × $0.0376 | $27.45 |
| PR agent compute | 100 × $0.0752 | $7.52 |
| Release agent compute | 20 × $0.0752 | $1.50 |
| Encrypted gp3 disks | 260 GiB total × assumed $0.08/GiB-month, baseline IOPS/throughput | $20.80 |
| Public IPv4 for egress | 850 running host-hours × $0.005 | $4.25 |
| Controller backups | Allowance for ~40 GiB aggregate retained billable snapshot data | $2.00 |
| CloudWatch logs | Modest ingestion/storage allowance; 14-day retention | $2.00 |
| Machine bootstrap secrets/API calls | Three secret containers, low request volume | $1.45 |
| CI ECR image storage | ~4 GiB allowance | $0.40 |
| S3 Ansible transfer scratch/requests | Low-volume allowance | $0.10 |
| Network transfer | Allowance; no assumption that account free allowances remain unused | $2.00 |
| NAT gateway, ALB, private endpoints, paid private CA | None in this design | $0.00 |
| **Nominal Jenkins subtotal** | Reproduce with `python scripts/estimate-jenkins-cost.py` | **$69.47** |

Plan **$70–$85/month additional** for this usage pattern. Disk/snapshot churn, logs, registry storage, transfer and build hours are estimates, not verified account usage or a spending cap. Storage/network unit assumptions must be reconfirmed in the regional AWS calculator before apply. Relevant primary pricing: [EBS](https://aws.amazon.com/ebs/pricing/), [public IPv4](https://aws.amazon.com/vpc/pricing/), [EC2](https://aws.amazon.com/ec2/pricing/on-demand/), [CloudWatch](https://aws.amazon.com/cloudwatch/pricing/), [Secrets Manager](https://aws.amazon.com/secrets-manager/pricing/), [ECR](https://aws.amazon.com/ecr/pricing/), [S3](https://aws.amazon.com/s3/pricing/), [Backup](https://aws.amazon.com/backup/pricing/). [Session Manager has no additional EC2 usage charge](https://aws.amazon.com/systems-manager/pricing/).

If both agents are left running all month, Jenkins rises to approximately **$176.94/month additional**, with combined application + Jenkins planning spend around **$262–$287/month**. Keep agent start/stop discipline and alerts; do not present the low-hours estimate as an always-on price.

The application's existing estimate is $85–$110/month, not a new measurement of actual billing. Combined expected spend is therefore **$155–$195/month** with agents used as planned. The existing `$100/month` budget has no email notification and, in the checked-in Terraform, no cost filter: it covers account-wide cost. The owner approved increasing this to **$220/month**, alerts to the verified billing/contact email, and a separate **one-off $2 allowance** for an approximately four-hour disposable AWS host test. The budget change has not been applied. Budgets alert; they do not cap charges.

Updating the existing account budget must be reviewed/applied through its current `single-account` ownership with the current application image tag preserved. The hosting root does not create a competing budget or silently change that existing resource. Any unexpected application/data-resource change in that administrative plan must stop the operation.

## Access, HTTPS and authentication

- No public ingress to Jenkins, SSH, port 8080, or agent TCP 50000. Public IPv4 exists only for outbound TLS without a NAT gateway. Controller security group allows TCP 8443 only from validation/release security groups over private addresses; agents have no inbound rules. Administration uses an IAM-authorized SSM tunnel to the controller, authenticated with the administrator's own Identity Center assignment and MFA.
- Intended URL: `https://jenkins.internal:8443`, resolved to the controller's private IP on agents and to localhost for an administrator's SSM tunnel. HTTPS must be configured with a host-generated internal certificate/CA on the encrypted controller volume; distribute only the public trust certificate to agents/admins. Certificate trust, expiry monitoring and rotation must be tested before enabling jobs. Never disable certificate verification.
- Controller runs Jenkins in Docker without a Docker socket and with zero executors. Use a current scanned/pinned controller image, CSRF protection, authentication, no anonymous access, restricted job configuration/replay/approvals, and a newly generated machine bootstrap admin secret fetched into runtime memory from its own Secrets Manager container. Never copy a developer password or SSO session. Configure the approved Identity Center/SSO integration and recovery admin before production cutover; no unconfigured login or public service is started by this proposal.
- Agents use WebSocket over HTTPS. Register separate machine identities/secrets. Configure and verify agent/job authorization so an untrusted PR requesting `echoscript-release` is denied; labels alone are not a security boundary. Keep Agent-to-Controller protections enabled. Test the denial explicitly before allowing untrusted builds. Never place release credentials on a PR agent or share daemons/workspaces across these trust levels.

HTTPS termination, controller/agent image assembly, node registration/authorization and production service units still require implementation and live testing after this cost/access design is approved. The new Ansible role is a guarded **host foundation**, not a claim that those runtimes are already operational.

## AWS identity and secrets

Use the new developer profile `giri` only after configuring it with that developer's **own** Identity Center assignment and completing their own login. No AWS profiles were available in the inspected local profile list; no previous developer session was opened or copied. The user requested the account-associated email for alerts: verify the billing alternate contact using authorized `account:GetAlternateContact` access after login; if unavailable, require the account owner's confirmation. Do not guess an address or send it to someone unrelated.

The proposed AWS-native machine identity uses the EC2 release host's automatically rotated instance-profile credentials to assume the five scoped job roles for **900 seconds**. Validation/controller roles cannot assume application deployment roles. `ci/scripts/machine_profile.py` permits only root-owned, fixed machine profiles with `credential_source=Ec2InstanceMetadata`; SSO fields, static keys, source profiles, wrong accounts and arbitrary profiles are rejected. Shared credential files are disabled. The existing OIDC mode remains supported for an approved issuer/broker. Neither mode borrows developer SSO.

Render application role permissions with `ci/iam/render.py` using confirmed existing ECR/backend/distribution/service metadata. Review the exact policies with IAM Access Analyzer and the real plan before installing them. The hosting root creates these roles with trust only for the release host role; no existing application role is independently owned or modified by Ansible. Empty Secrets Manager containers contain no values in Terraform state; populate new machine secrets through an approved out-of-band process, never Git or terminal logs.

## Ansible and AWS test sequence

Inventory: `infrastructure/ansible/inventories/jenkins.aws_ec2.yml`. It selects only running hosts in the same account/region with `Project=echoscript-jenkins`, connects through `amazon.aws.aws_ssm`, and uses the new dedicated encrypted, private transfer bucket. Do not put secret values in Ansible module payloads or inventory. The SSM connection uses temporary S3 transport; scratch expires after one day and is distinct from application buckets. Controller-node permissions for SSM/S3 transport must be approved separately; no developer credentials are sent to targets.

The reusable `jenkins_host` role installs Docker from Ubuntu packages using idempotent modules, configures log rotation and root-owned non-secret host policy, and installs fixed role profiles only on the trusted release host. It rejects wrong platforms/connections and production configuration before a disposable-host pass is recorded. It does not manage ECS, S3 application data, DynamoDB, or application Terraform resources.

After cost approval, first enable the optional disposable host, verify its ID/role/account, and run:

```bash
export AWS_PROFILE=giri AWS_REGION=us-west-2
cd infrastructure/ansible
ansible-lint --offline
ansible-playbook -i inventories/jenkins.aws_ec2.yml playbooks/jenkins-hosts.yml --syntax-check
ansible-playbook -i inventories/jenkins.aws_ec2.yml playbooks/jenkins-hosts.yml --limit jenkins_disposable --check --extra-vars @/secure/approved-host-vars.yml
ansible-playbook -i inventories/jenkins.aws_ec2.yml playbooks/jenkins-hosts.yml --limit jenkins_disposable --extra-vars @/secure/approved-host-vars.yml
# Repeat apply and check; record changed=0, failed=0, unreachable=0.
```

The operations control environment needs the official AWS CLI/Session Manager plugin and pinned `amazon.aws` collection; do not execute these commands until the approved host and own login exist. Only after its evidence is recorded may `jenkins_host_disposable_checks_passed` be set for production targets. Configure runtime HTTPS/authentication/agents, verify access denial and backups, then run a real **AWS-hosted** pipeline and archive build URL/SHA/tools/scans/plan/approval/apply/smoke/rollback evidence. Historical Docker tests do not satisfy this AWS-target requirement.

Cleanup of the disposable test host must use a separately reviewed normal Terraform change disabling only that optional host, preserving controller data/backups and the application. Never run `terraform destroy`, target application buckets/tables, or delete application data. Its empty test bootstrap secret uses a recovery window. Stop agents when finished to avoid continued compute/IPv4 charges.

## Persistence, patching, logging and recovery

The separate encrypted 40 GiB controller data disk has Terraform `prevent_destroy`; controller termination protection and retained root disk provide additional safeguards. Only the Jenkins data volume is selected by the proposed daily AWS Backup plan, with 14-day recovery-point retention. The selection does not include application data. Automated EBS recovery points are crash-consistent until a quiesced Jenkins backup/restore procedure is implemented and tested; do not claim application-consistent backup or a proven RTO yet.

Target RPO is 24 hours; initial RTO planning target is two hours, pending a restore drill. Recovery must restore to a new isolated Jenkins data volume, rebuild an approved OS with Ansible, restore Jenkins keys/configuration and internal TLS material, verify authentication/node authorization, rotate bootstrap/agent secrets if needed, and reconnect agents. Keep release jobs disabled until checks pass. Production transcription remains on its existing ECS/Fargate path throughout a Jenkins outage.

Plan monthly OS/Docker/Jenkins/plugin security updates, earlier emergency patches, digest-pinned scanned images, coordinated agent/controller maintenance, and a backup before upgrades. Enable scoped CloudWatch container/system logs and Jenkins audit events with retention; never log bootstrap secrets, JWTs, secret scan details, signed URLs or decrypted plans. Log shipping, host runtime configuration, backup consistency and recovery must be verified on AWS before operational acceptance.

## Current evidence and remaining prerequisites

Backend-free Terraform fmt/validate passed for the proposal using the existing signed AWS 6.72.0 provider; no provider upgrade, AWS backend init, plan/apply, or cloud API resource change occurred. Eighteen CI safety tests passed, including three new machine-profile tests. Ansible production-profile lint and AWS playbook syntax passed; **no AWS check-mode/apply/idempotence test has run**. Existing application checks/scans and historical local pipeline evidence remain in [ci-verification.md](ci-verification.md).

Cost approval is recorded above and in `ci/jenkins-cost-estimate.json`. A fresh `aws configure list-profiles` check after approval still returned no configured profiles. Browser sign-in automation was unavailable; no login, credential copying or AWS provisioning occurred. The developer must configure and sign into their own `giri` Identity Center profile. Then verify account/role, backend, billing contact, AMI and policies, review the provisioning plan, and perform the AWS target tests. No further cost confirmation is needed for the approved scope.
