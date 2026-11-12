# EchoScript AWS Jenkins pilot runbook

This runbook deploys only the Jenkins hosting root in `infrastructure/terraform/jenkins-hosting`. It does not provision resources automatically. Work from branch `giri` in the repository root. Jenkins uses the separate state key `echoscript/jenkins-hosting/terraform.tfstate`; the production application key remains `echoscript/prod/terraform.tfstate` and must never be replaced, migrated, imported, or passed to this root.

The runtime is not yet AWS accepted. The commands below are the next sequence after the blockers at the end of this runbook are resolved. No AWS deployment has been performed by this implementation.

## 1. Verify operator, tools, and policy gate

Use the operator's own IAM Identity Center profile and session. Do not copy credentials from another developer or use static access keys.

```powershell
$env:AWS_PROFILE = 'giri'
$env:AWS_REGION = 'us-west-2'
aws sts get-caller-identity
aws configure list
python -m unittest discover -s ci/tests -v
terraform -chdir=infrastructure/terraform/jenkins-hosting fmt -check -recursive
terraform -chdir=infrastructure/terraform/jenkins-hosting init -backend=false -input=false -lockfile=readonly
terraform -chdir=infrastructure/terraform/jenkins-hosting validate
```

Confirm the caller is account `598391748654`, region `us-west-2`, and the intended human operator. Obtain the actual existing encrypted Terraform state bucket and lock table from the authorized state owner. Do not run `infrastructure/terraform/bootstrap-state`. The hosting root's preconditions still require explicit cost approval, an approved account-wide monthly budget of at least **$220**, and all five reviewed application role policies. Keep both approval gates in place; do not fill their values merely to make a plan succeed. Verify current budget monitoring and account spend/headroom separately. The hosting root has no billing-email input and does not change the existing application's AWS Budget or notification subscribers. The budget is an alert, not a spending cap. The existing application root and Terraform state remain separately owned.

Create `C:/secure/jenkins.tfvars` outside Git with verified values only:

```hcl
cost_approval_reference  = "<APPROVED_REFERENCE>"
approved_account_budget_usd = 220
ubuntu_ami_id            = "<PINNED_UBUNTU_24_04_AMI>"
application_role_policies = {
  publish  = "<REVIEWED_JSON_POLICY>"
  plan     = "<REVIEWED_JSON_POLICY>"
  deploy   = "<REVIEWED_JSON_POLICY>"
  frontend = "<REVIEWED_JSON_POLICY>"
  smoke    = "<REVIEWED_JSON_POLICY>"
}
```

The policy JSON must be generated from confirmed live resource metadata with `ci/iam/render.py` and reviewed. Do not put secret values in Terraform variables. Confirm the approved account budget, its existing monitoring, and actual spend independently; an approved `220` input is not a way around that review.

The API is declared in `infrastructure/terraform/single-account/application.tf` as an `aws_ecs_express_gateway_service` named from the `echoscript-prod` prefix. It does not belong to the `echoscript-prod-workers` service cluster; because no cluster is specified, ECS Express Mode uses the `default` cluster. The zero-service result for `echoscript-prod-workers` therefore does not show that the API is absent. Discover and verify its live ARN read-only before rendering IAM policies:

```powershell
aws ecs list-services --cluster default --region us-west-2 --output json
$apiServiceArn = '<COPY_EXACT_ECHOSCRIPT_PROD_API_ARN_FROM_OUTPUT>'
if ($apiServiceArn -notmatch '^arn:aws:ecs:us-west-2:598391748654:service/') { throw 'Unexpected API service ARN' }
aws ecs describe-services --cluster default --services $apiServiceArn --region us-west-2 --output json
```

Confirm `serviceName` is `echoscript-prod-api` and copy the exact ARN into the renderer's `--api-service-arn` argument. If the default-cluster listing does not return it, read the existing application's Terraform resource from its already initialized, authorized workspace (`terraform state show aws_ecs_express_gateway_service.api`). Do not initialize/reconfigure that backend or alter its state for this lookup. The renderer intentionally retains the exact service ARN requirement so `ecs:UpdateExpressGatewayService` is scoped to the API.

## 2. Initialize only the Jenkins state and review a saved plan

Use the exact existing bucket and lock table; do not copy the placeholders below literally. Keep the state key exact.

```powershell
$stateBucket = '<EXISTING_ENCRYPTED_STATE_BUCKET>'
$lockTable = '<EXISTING_STATE_LOCK_TABLE>'
$stateKey = 'echoscript/jenkins-hosting/terraform.tfstate'
if ($stateKey -ne 'echoscript/jenkins-hosting/terraform.tfstate') { throw 'Wrong Jenkins state key' }
terraform -chdir=infrastructure/terraform/jenkins-hosting init -input=false `
  -backend-config="bucket=$stateBucket" `
  -backend-config="key=$stateKey" `
  -backend-config="region=us-west-2" `
  -backend-config="dynamodb_table=$lockTable" `
  -backend-config="encrypt=true"
terraform -chdir=infrastructure/terraform/jenkins-hosting plan -input=false `
  -var-file='C:/secure/jenkins.tfvars' `
  -out='C:/secure/jenkins-pilot.tfplan'
terraform -chdir=infrastructure/terraform/jenkins-hosting show 'C:/secure/jenkins-pilot.tfplan'
```

Review every resource and IAM action. Stop if the plan refers to the application state key, application resources, public ingress, broad permissions, a changed budget outside its owner-approved process, or deletion/replacement of any state/data resource. The Jenkins controller data volume has `prevent_destroy`; preserve it and all recovery points. Do not use `-target`, state surgery, state migration, or `terraform destroy`.

Apply only the exact reviewed saved plan, after the operator's normal approval:

```powershell
terraform -chdir=infrastructure/terraform/jenkins-hosting apply -input=false 'C:/secure/jenkins-pilot.tfplan'
terraform -chdir=infrastructure/terraform/jenkins-hosting output -json
```

## 3. Configure the host foundation through SSM

Install the pinned Ansible collections in the approved operations environment and confirm the SSM plugin is available. Set the values from Terraform outputs and privately seed the Secrets Manager containers out-of-band. Do not put passwords, agent tokens, or certificate private keys in Git, Terraform, command-line arguments, or build logs.

The controller secret `echoscript/jenkins/controller/bootstrap` must contain `admin_password`, unique `pr_validator_id`/`pr_validator_password`, unique `release_operator_id`/`release_operator_password`, unique `release_approver_id`/`release_approver_password`, a read-only `github_token`, and the public `tf_plan_recipient` age recipient. Use random passwords of at least 32 characters. Seed only `smoke_token` and base64 encoded `smoke_audio_base64` in `echoscript/jenkins/release/bootstrap`; validation has no production fixture. Do not seed fabricated `agent_secret` or CA values. Stage A retrieves each node's generated token through authenticated TLS JNLP and adds `agent_secret` plus public `controller_ca_pem` to each role-specific secret. The validation secret contains no smoke fields. Secret payloads are read and written under Ansible `no_log`; never print them.

Build and publish the custom inbound agent image to the immutable CI ECR repository before starting agents. Use the operator's own SSO backed AWS session for this initial bootstrap; no access key is used:

```powershell
$registry = '598391748654.dkr.ecr.us-west-2.amazonaws.com'
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $registry
docker build -f ci/agent/Dockerfile -t "$registry/echoscript/jenkins/agent:pilot-1" .
docker push "$registry/echoscript/jenkins/agent:pilot-1"
docker logout $registry
```

The agent image derives from the inbound-agent image, installs the CI toolchain, and imports the mounted public CA into a temporary Java truststore at startup. CI builds/tests use the separate `moby/buildkit:v0.34.1-rootless` sidecar with per-agent cache volumes; the agent image itself has no Docker CLI/socket. Scan and pin the agent, BuildKit, controller, and proxy images by digest before production acceptance. The immutable agent repository accepts distinct tags, but never overwrite an existing tag.

Run the disposable host checks first (optional host is disabled by default). Then configure the controller:

```powershell
ansible-galaxy collection install -r infrastructure/ansible/requirements.yml
ansible-inventory -i infrastructure/ansible/inventories/jenkins.aws_ec2.yml --graph
ansible-playbook -i infrastructure/ansible/inventories/jenkins.aws_ec2.yml infrastructure/ansible/playbooks/jenkins-hosts.yml `
  --limit jenkins_controller `
  --extra-vars "jenkins_host_approval_reference=<APPROVED_REFERENCE> jenkins_host_disposable_checks_passed=true jenkins_host_role=controller jenkins_controller_volume_id=<CONTROLLER_VOLUME_ID> jenkins_backup_bucket=<BACKUP_BUCKET>"
```

Stage A initializes the controller, configures both inbound WebSocket nodes, waits for HTTPS health, retrieves the generated node tokens through authenticated JNLP, and securely writes them plus the public CA into the separate Secrets Manager payloads. Confirm the controller's completion output reports updated/current bootstrap values; it never prints tokens. Stage B configures the agents, installs their role-specific CA trust, and verifies both nodes online. Agents remain stopped unless explicitly requested. Run the controller stage first, then Stage B with `jenkins_agent_start=true` only for an approved acceptance window:

```powershell
ansible-playbook -i infrastructure/ansible/inventories/jenkins.aws_ec2.yml infrastructure/ansible/playbooks/jenkins-hosts.yml `
  --limit jenkins_controller `
  --extra-vars "jenkins_host_approval_reference=<APPROVED_REFERENCE> jenkins_host_role=controller jenkins_controller_volume_id=<CONTROLLER_VOLUME_ID> jenkins_backup_bucket=<BACKUP_BUCKET>"
ansible-playbook -i infrastructure/ansible/inventories/jenkins.aws_ec2.yml infrastructure/ansible/playbooks/jenkins-agents.yml `
  --extra-vars "jenkins_host_approval_reference=<APPROVED_REFERENCE> jenkins_host_disposable_checks_passed=true jenkins_controller_private_ip=<CONTROLLER_PRIVATE_IP> jenkins_agent_start=true"
```

Stop both agent services after acceptance and keep their instances stopped when idle. Start a specific agent only when its role is needed. The validation IMDSv2 response hop limit is one, so its untrusted jobs cannot obtain EC2 role credentials; BuildKit runs on a separate bridge network without metadata access. The release agent uses host networking for its scoped instance profile; its BuildKit sidecar remains on bridge networking and receives no instance profile.

Controller admin access is private: add `jenkins.internal` to the operator's temporary hosts mapping for the controller's private IP, establish an SSM port-forward to TCP 8443, and trust the public CA certificate. Never open port 22, 8080, 50000, or 8443 to the internet. Security groups allow 8443 only from the two agent security groups; host public IPv4 is for outbound TLS only.

## 4. GitHub PR and release controls

The authoritative SCM source is `https://github.com/DevUtkarsh098/EchoScript`, on branch `giri`. Jenkins obtains its existing fine-grained PAT from `echoscript/jenkins/controller/bootstrap`; do not create another token. Confirm repository visibility and PAT access before activating source indexing.

JCasC seeds `EchoScript-PR` from GitHub branch and pull-request discovery, polling every two minutes, and uses `ci/Jenkinsfile.validation` on the isolated `echoscript-validation` agent. It grants `pr-validator` only read/build on the PR job. Since multibranch child jobs inherit the global anonymous build identity, anonymous receives only `Agent/Build` on the validation node; it has no overall, job, credential, configuration, or release-agent permissions. Authorize Project sets the protected release job to run only as `release-operator`. The validation host has no deployment role. Jenkins has zero controller executors and no anonymous UI/job access.

JCasC seeds `EchoScript-Release` from the reviewed `giri` branch and `ci/Jenkinsfile.delivery`. Only `release-operator` can start it; `release-approver` is the named `input` approver. JCasC supplies the approver ID and public `TF_PLAN_RECIPIENT` only to the release node; the smoke token and audio fixture are mounted read-only only on the release agent. The pipeline checks out `giri`, rejects PR metadata, uses separate short-lived IAM roles, and applies only the same saved plan after explicit approval.

In GitHub repository settings, protect `giri`: require pull requests, at least one independent approval, dismiss stale approvals, require the PR validation status check, require branches to be current, prohibit force pushes/deletion, and restrict bypass to named maintainers. Require a release review/tag policy that records the immutable source SHA. Configure no incoming public webhook because the Jenkins endpoint is private; the configured SCM polling provides PR discovery. If a private GitHub App or relay is later introduced, keep the endpoint private and validate its signature before enabling event delivery.

Webhook setup reference for a later private relay: Jenkins GitHub integration receives repository events at `https://jenkins.internal:8443/github-webhook/`. The GitHub App/webhook should subscribe only to `pull_request` (opened, synchronize, reopened, closed) and `push` for `giri`, use a dedicated least-privilege app identity, and rotate its webhook secret through Secrets Manager. A relay must verify GitHub's HMAC signature before forwarding, reject replayed/old deliveries, and reach only the private controller over TLS. Do not add a public load balancer, public security-group rule, or disable certificate checking to make delivery work. Until that relay is approved and tested, retain two-minute SCM polling.

Acceptance checks (record build URLs, commit SHA, and denial evidence):

- Anonymous requests to the tunneled Jenkins URL cannot view jobs or authenticate; admin, PR, release, and approver accounts have only their documented permissions.
- `pr-validator` can start PR validation, cannot configure/replay the release job, cannot start it, and cannot use the release node. Test each denial explicitly.
- A fork PR that requests the release label is denied the release agent and cannot access release IAM, production secrets, or release credentials. Verify its AWS identity is absent and it cannot assume any application role.
- The protected release job runs only the reviewed `giri` SHA, requires the named independent approver, and applies only the archived saved plan after approval.
- Both agents connect over WebSocket/HTTPS with valid certificate verification; public ingress scan shows no SSH/Jenkins ports.
- A daily backup exists in the encrypted S3 bucket and the AWS Backup vault; perform a restore drill to an isolated host and confirm credentials, job configuration, CA trust, and node authorization recover before enabling releases.
- Run an AWS-hosted validation build and an approved release rehearsal. Archive the build URL, SHA, scan results, plan summary, approval identity, apply result, smoke result, and rollback evidence.

## Backup, restore, and seven-day shutdown

The controller quiesces Jenkins during its daily home backup, streams the full home (including credentials and job config) to S3 with AES-256 server-side encryption, and uses bucket versioning plus 14-day object/version retention. An independent daily AWS Backup EBS recovery point covers the encrypted controller data volume with 14-day retention. The latter also protects `/mnt/jenkins-data/tls`, including the private CA. Check both backup systems and CloudWatch/service logs after every run; restore testing remains an acceptance gate.

For recovery, keep release jobs disabled. Create an isolated replacement controller in the same private network, attach a new encrypted data volume, restore the latest S3 archive into an empty Jenkins home using the controller instance role, and restore the matching EBS recovery point for `/mnt/jenkins-data/tls`. After Ansible mounts the new volume and before Jenkins starts, enter an SSM shell on the replacement controller and run:

```bash
sudo systemctl stop echoscript-jenkins
sudo install -d -o 1000 -g 1000 -m 0750 /mnt/jenkins-data/home
set -o pipefail
aws s3 cp 's3://<JENKINS_BACKUP_BUCKET>/jenkins-home/<UTC_BACKUP_FILENAME>.tar.gz' - --region us-west-2 \
  | sudo tar --numeric-owner --acls --xattrs -xzf - -C /mnt/jenkins-data/home
sudo chown -R 1000:1000 /mnt/jenkins-data/home
sudo systemctl start echoscript-jenkins
```

The filename is selected from the retained `jenkins-home/` keys by the authorized operator. Restore the matching EBS recovery point to the new data volume so the CA private key and certificate agree with the S3-restored jobs and credentials. Reapply Ansible, verify the CA and HTTPS endpoint, rotate all bootstrap and agent secrets, confirm authorization and node restrictions, then run the denial checks and backup drill. Keep the old volume and recovery points until the owner accepts the restored controller. Do not restore over the only surviving copy.

At the end of the seven-day pilot:

1. Stop accepting PR/release work; verify no build, approval, apply, or rollback is active.
2. Stop both agent services and stop both agent EC2 instances by their exact Terraform output IDs. Confirm no release credentials or session remains active.
3. Export audit/build evidence, confirm a recent S3 archive and AWS Backup recovery point, and save the restore-drill record.
4. Disable `EchoScript-PR` and `EchoScript-Release`; revoke bootstrap/GitHub credentials and rotate any retained admin credentials.
5. Review actual spend and the next month's account budget alert. Stop the controller only if retention policy and restore access have been explicitly resolved.
6. Do not destroy resources or remove state. This root has no safe pilot teardown switch, and the controller data volume is protected by `prevent_destroy`. A separately reviewed change is required to decommission compute while retaining the controller volume, backups, and audit evidence. Never run `terraform destroy`.

Stopping instances does not stop all charges: EBS volumes, S3 versions, AWS Backup recovery points, logs, ECR images, Secrets Manager secrets, and public IPv4 addresses while instances run may continue billing. The checked-in estimate assumes 100 validation and 20 release agent hours/month and is approximately $69.97/month nominal ($70–$85 planning range), including a $0.50 S3 home-backup storage allowance, with the controller on continuously. Both agents running continuously raises the hosting estimate to about $177.44/month. Existing application spend is estimated at $85–$110/month; actual spend and network/storage usage vary. Budgets alert and do not cap charges.

## Current blockers

- No AWS resources have been provisioned or tested. State bucket/table names, pinned AMI, live application role metadata/policies, current account budget monitoring/spend, and operator identity must be verified by the authorized operator.
- The `$220` Terraform precondition is intentionally preserved. The plan cannot proceed until its owner inputs are verified and approved; do not alter or bypass it.
- Jenkins/Ansible/Terraform are not installed in this Windows execution environment. Python tests run locally, but shell integration and age-encryption tests require a POSIX CI image with Bash and `age`/`age-keygen`.
- Jenkins JCasC, plugin compatibility, job creation, role denials, inbound token flow, and live certificate rotation have not been exercised on a controller. Confirm the pinned plugin versions and resulting JCasC schema in the disposable AWS test before production hosts.
- Controller, agent, and proxy container images still need digest pinning and scanning. Agent node tokens must be provisioned from the controller into separate Secrets Manager secrets after node creation.
- GitHub branch protection, real GitHub polling, AWS authorization denial, S3/EBS backup, restore, and the saved-plan approval path require live pilot evidence.
- The runbook uses the existing no-public-ingress design. The EC2 hosts have public IPv4 for outbound TLS; there is no public Jenkins, SSH, or agent TCP ingress.
