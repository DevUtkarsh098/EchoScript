"""Fail-closed checks for the checked-in Jenkins trust boundaries."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[2]
CAS = ROOT / 'infrastructure/ansible/roles/jenkins_host/templates/controller-casc.yml.j2'


class JenkinsSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.casc = CAS.read_text(encoding='utf-8')
        cls.pr = (ROOT / 'ci/Jenkinsfile.validation').read_text(encoding='utf-8')
        cls.release = (ROOT / 'ci/Jenkinsfile.delivery').read_text(encoding='utf-8')
        cls.iam = (ROOT / 'infrastructure/terraform/jenkins-hosting/identity.tf').read_text(encoding='utf-8')

    def test_controller_has_zero_executors_and_explicit_role_authorization(self):
        self.assertIn('numExecutors: 0', self.casc)
        self.assertIn('authorizationStrategy:', self.casc)
        self.assertIn('roleBased:', self.casc)
        self.assertIn('Overall/Administer', self.casc)
        self.assertNotIn('Job/Configure', self.casc)
        self.assertIn('anonymousAuthorizationStrategy', self.casc)
        self.assertIn("pattern: \"EchoScript-PR(/.*)?\"", self.casc)
        self.assertIn("pattern: \"EchoScript-Release\"", self.casc)
        pr_role = self.casc.split('          - name: pr-builders', 1)[1].split('          - name: release-operators', 1)[0]
        release_role = self.casc.split('          - name: release-operators', 1)[1].split('          - name: release-approvers', 1)[0]
        approver_role = self.casc.split('          - name: release-approvers', 1)[1].split('        agents:', 1)[0]
        self.assertIn('Job/Build', pr_role)
        self.assertNotIn('Job/Configure', pr_role)
        self.assertNotIn('Job/Build', approver_role)
        self.assertIn('Job/Build', release_role)
        self.assertNotIn('Job/Configure', release_role)
        global_roles = self.casc.split('        global:', 1)[1].split('        items:', 1)[0]
        self.assertNotIn('anonymous', global_roles.lower())
        self.assertIn("userid(System.getenv('RELEASE_OPERATOR_ID'))", self.casc)
        validation_agent = self.casc.split('          - name: validation-agent', 1)[1].split('          - name: release-agent', 1)[0]
        release_agent = self.casc.split('          - name: release-agent', 1)[1].split('  nodes:', 1)[0]
        self.assertIn('Agent/Build', validation_agent)
        self.assertIn('anonymous', validation_agent)
        self.assertIn('Agent/Build', release_agent)
        self.assertIn('${RELEASE_OPERATOR_ID}', release_agent)
        self.assertNotIn('${PR_VALIDATOR_ID}', release_agent)

    def test_pr_pipeline_is_untrusted_validation_only(self):
        self.assertIn("node('echoscript-validation')", self.pr)
        self.assertNotIn('awsRole(', self.pr)
        self.assertNotIn('withCredentials', self.pr)
        self.assertNotIn('echoscript-release', self.pr)
        self.assertIn("node('echoscript-release')", self.release)
        self.assertIn('env.CHANGE_ID || env.CHANGE_URL', self.release)
        self.assertIn('RELEASE_APPROVERS', self.release)
        self.assertIn("branch('*/{{ jenkins_host_github_branch }}')", self.casc)
        self.assertIn('github {', self.casc)
        validation_node = self.casc.split('name: echoscript-validation', 1)[1].split('name: echoscript-release', 1)[0]
        self.assertNotIn('SMOKE_TOKEN_FILE', validation_node)
        self.assertNotIn('TF_PLAN_RECIPIENT', validation_node)

    def test_release_iam_is_attached_only_to_release_host(self):
        self.assertIn('each.key == "release"', self.iam)
        self.assertIn('sts:AssumeRole', self.iam)
        self.assertIn('aws_iam_role.node["release"].arn', self.iam)
        self.assertNotIn('aws_iam_role.node["validation"].arn', self.iam)

    def test_pr_host_has_no_deployment_role_and_controller_has_backup_only(self):
        release_agent = self.iam.index('each.key == "release"')
        backup = self.iam.index('each.key == "controller"')
        self.assertLess(backup, release_agent)
        self.assertIn('s3:PutObject', self.iam)
        self.assertIn('secretsmanager:GetSecretValue', self.iam)
        self.assertNotIn('aws_iam_role.deployment : role.arn', self.iam[:release_agent])

    def test_agents_use_websocket_and_start_stopped(self):
        agent = (ROOT / 'infrastructure/ansible/roles/jenkins_host/templates/agent-compose.yml.j2').read_text(encoding='utf-8')
        tasks = (ROOT / 'infrastructure/ansible/roles/jenkins_host/tasks/agent.yml').read_text(encoding='utf-8')
        service = (ROOT / 'infrastructure/ansible/roles/jenkins_host/templates/jenkins-agent.service.j2').read_text(encoding='utf-8')
        image = (ROOT / 'ci/agent/Dockerfile').read_text(encoding='utf-8')
        entrypoint = (ROOT / 'ci/agent/entrypoint.sh').read_text(encoding='utf-8')
        self.assertIn('JENKINS_WEB_SOCKET: "true"', agent)
        self.assertIn('jenkins-ca.crt:/run/jenkins/jenkins-ca.crt:ro', agent)
        self.assertIn('keytool -importcert', entrypoint)
        self.assertIn('FROM jenkins/inbound-agent:', image)
        self.assertIn('ExecStartPre=/usr/local/sbin/echoscript-jenkins-agent-ecr-auth login', service)
        self.assertIn('ExecStopPost=/usr/local/sbin/echoscript-jenkins-agent-ecr-auth logout', service)
        self.assertIn("else 'stopped'", tasks)
        self.assertIn('enabled: false', tasks)
        self.assertIn('smoke_audio_base64', tasks)
        self.assertIn("when: jenkins_host_role == 'release'", tasks)
        self.assertIn('jenkins/secrets:/run/echoscript-secrets:ro', agent)
        self.assertIn('SMOKE_TOKEN_FILE:', agent)
        self.assertIn('SMOKE_AUDIO_FILE:', agent)
        self.assertNotIn('/var/run/docker.sock', agent)
        self.assertNotIn('group_add:', agent)
        self.assertIn('image: {{ jenkins_host_buildkit_image }}', agent)
        self.assertIn('cap_drop: [ALL]', agent)
        self.assertIn('cap_add: [SETUID, SETGID]', agent)
        self.assertNotIn('privileged:', agent)
        self.assertIn('buildkit-state', agent)
        self.assertIn('http_put_response_hop_limit = 1', (ROOT / 'infrastructure/terraform/jenkins-hosting/main.tf').read_text(encoding='utf-8'))
        pr_node = self.casc.split('name: echoscript-validation', 1)[1].split('name: echoscript-release', 1)[0]
        release_node = self.casc.split('name: echoscript-release', 1)[1].split('unclassified:', 1)[0]
        self.assertNotIn('SMOKE_', pr_node)
        self.assertIn('SMOKE_TOKEN_FILE', release_node)
        self.assertIn('RELEASE_APPROVERS', release_node)
        self.assertIn('TF_PLAN_RECIPIENT', release_node)

    def test_tls_and_recovery_configuration_are_present(self):
        controller = (ROOT / 'infrastructure/ansible/roles/jenkins_host/tasks/controller.yml').read_text(encoding='utf-8')
        terraform = (ROOT / 'infrastructure/terraform/jenkins-hosting/storage.tf').read_text(encoding='utf-8')
        self.assertIn('validate_certs: true', controller)
        self.assertIn('ca_path:', controller)
        self.assertIn('aws_backup_selection', terraform)
        self.assertIn('delete_after = 14', terraform)
        self.assertIn('encrypted         = true', (ROOT / 'infrastructure/terraform/jenkins-hosting/main.tf').read_text(encoding='utf-8'))
        s3 = (ROOT / 'infrastructure/terraform/jenkins-hosting/storage.tf').read_text(encoding='utf-8')
        backup = (ROOT / 'infrastructure/ansible/roles/jenkins_host/templates/backup-jenkins-home.sh.j2').read_text(encoding='utf-8')
        self.assertIn('aws_s3_bucket.jenkins_backup', s3)
        self.assertIn('days = 14', s3)
        self.assertIn('--sse AES256', backup)
        self.assertIn('systemctl stop', backup)
        self.assertIn('trap restart_controller EXIT', backup)
        renewal = (ROOT / 'infrastructure/ansible/roles/jenkins_host/templates/renew-certificate.sh.j2').read_text(encoding='utf-8')
        self.assertIn('checkend 2592000', renewal)
        self.assertIn('systemctl restart echoscript-jenkins', renewal)
        ansible_collections = (ROOT / 'infrastructure/ansible/requirements.yml').read_text(encoding='utf-8')
        self.assertIn('ansible.posix', ansible_collections)
        self.assertIn('community.general', ansible_collections)

    def test_controller_compose_requires_every_casc_variable(self):
        compose = (ROOT / 'infrastructure/ansible/roles/jenkins_host/templates/controller-compose.yml.j2').read_text(encoding='utf-8')
        for key in ('JENKINS_ADMIN_ID', 'JENKINS_ADMIN_PASSWORD', 'GITHUB_TOKEN', 'PR_VALIDATOR_ID',
                    'PR_VALIDATOR_PASSWORD', 'RELEASE_OPERATOR_ID', 'RELEASE_OPERATOR_PASSWORD',
                    'RELEASE_APPROVER_ID', 'RELEASE_APPROVER_PASSWORD', 'TF_PLAN_RECIPIENT'):
            self.assertIn(f'{key}: ${{{key}:?', compose)
        controller = (ROOT / 'infrastructure/ansible/roles/jenkins_host/tasks/controller.yml').read_text(encoding='utf-8')
        self.assertIn("mode: '0600'", controller)

    def test_two_stage_agent_bootstrap_is_authenticated_idempotent_and_tls_verified(self):
        helper = (ROOT / 'infrastructure/ansible/roles/jenkins_host/files/bootstrap-agent-secrets.py').read_text(encoding='utf-8')
        controller = (ROOT / 'infrastructure/ansible/roles/jenkins_host/tasks/controller.yml').read_text(encoding='utf-8')
        self.assertIn('/jenkins-agent.jnlp"', helper)
        self.assertNotIn('encrypt=true', helper)
        self.assertIn("'Authorization': f'Basic {auth}'", helper)
        self.assertIn('TemporaryDirectory', helper)
        self.assertIn('path.chmod(0o600)', helper)
        self.assertIn('--verify-online', helper)
        self.assertIn('bootstrap-agent-secrets.py', controller)
        self.assertIn('no_log: true', controller)
        self.assertIn('secretsmanager:PutSecretValue', self.iam)
        spec = importlib.util.spec_from_file_location('bootstrap_agent_secrets', ROOT / 'infrastructure/ansible/roles/jenkins_host/files/bootstrap-agent-secrets.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fixtures = {'smoke_token': 'test-smoke-token', 'smoke_audio_base64': 'dGVzdA=='}
        value = module.merge_agent_bootstrap(fixtures, 'a' * 40, 'test-ca-pem')
        self.assertEqual(module.merge_agent_bootstrap(value, 'a' * 40, 'test-ca-pem'), value)
        self.assertEqual(value['smoke_token'], fixtures['smoke_token'])

    def test_release_apply_requires_approval_and_applies_the_same_saved_plan(self):
        script = (ROOT / 'ci/Jenkinsfile.delivery').read_text(encoding='utf-8')
        release = (ROOT / 'ci/scripts/release.sh').read_text(encoding='utf-8')
        approval = script.index("stage('Explicit production approval')")
        apply = script.index("stage('Apply the same saved plan')")
        self.assertLess(approval, apply)
        self.assertIn('submitter: env.RELEASE_APPROVERS', script)
        self.assertIn('release.tfplan.sha256', release)
        self.assertIn('"$ROOT/ci-private/release.tfplan"', release)
        self.assertNotIn('terraform apply -auto-approve', release)

    def test_validation_builds_use_rootless_buildkit_without_host_docker(self):
        validate = (ROOT / 'ci/scripts/validate.sh').read_text(encoding='utf-8')
        image = (ROOT / 'ci/agent/Dockerfile').read_text(encoding='utf-8')
        build = (ROOT / 'ci/scripts/buildkit-build.sh').read_text(encoding='utf-8')
        self.assertNotIn('docker build', validate)
        self.assertNotIn('docker run', validate)
        self.assertIn('moby/buildkit:v0.34.1-rootless', image)
        self.assertIn('COPY --from=buildkit /usr/bin/buildctl', image)
        self.assertIn('buildctl', build)
        self.assertIn('AS ci-test', (ROOT / 'services/ingest-service/Dockerfile').read_text(encoding='utf-8'))
        self.assertIn('AS ci-test', (ROOT / 'services/transcribe-worker/Dockerfile').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
