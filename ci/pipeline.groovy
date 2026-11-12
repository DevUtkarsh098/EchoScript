def validate() {
    stage('Tool versions') { sh 'bash ci/scripts/validate.sh tools > ci-artifacts/tool-versions.txt' }
    stage('Secret scan and CI regression tests') { sh 'bash ci/scripts/validate.sh secrets' }
    stage('Frontend build') { sh 'bash ci/scripts/validate.sh frontend' }
    stage('Terraform fmt and validate') { sh 'bash ci/scripts/validate.sh terraform' }
    stage('API image and tests') { sh 'bash ci/scripts/validate.sh api' }
    stage('Worker image and tests') { sh 'bash ci/scripts/validate.sh worker' }
    stage('Ansible disposable target') { sh 'bash ci/scripts/validate.sh ansible' }
    stage('Docker images and Trivy gates') { sh 'bash ci/scripts/validate.sh images' }
}

def awsRole(String variable, Closure action) {
    def role = env[variable]
    def mode = env.AWS_JENKINS_CREDENTIAL_MODE ?: 'ec2-instance-profile'
    if (!role || mode != 'ec2-instance-profile') {
        error('Configure an approved Jenkins machine identity; no developer SSO or static-key fallback.')
    }
    def machineProfile = mode == 'ec2-instance-profile' ? "jenkins-${role.tokenize('/').last().replace('echoscript-jenkins-', '')}" : ''
    withEnv(["AWS_ROLE_ARN=${role}", "AWS_JENKINS_CREDENTIAL_MODE=${mode}", "AWS_PROFILE=${machineProfile}",
             'AWS_REGION=us-west-2', 'AWS_DEFAULT_REGION=us-west-2',
             "AWS_ROLE_SESSION_NAME=echoscript-${env.BUILD_NUMBER}",
             "AWS_EC2_METADATA_DISABLED=${mode == 'ec2-instance-profile' ? 'false' : 'true'}",
             "AWS_CONFIG_FILE=${mode == 'ec2-instance-profile' ? '/etc/echoscript/aws/config' : '/dev/null'}",
             'AWS_SHARED_CREDENTIALS_FILE=/dev/null']) {
        sh 'bash ci/scripts/aws-preflight.sh'
        action()
    }
}

def archiveEvidence() {
    archiveArtifacts artifacts: 'ci-artifacts/**', allowEmptyArchive: true, fingerprint: true
}

return this
