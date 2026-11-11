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
    if (!role || !env.AWS_WEB_IDENTITY_TOKEN_FILE) {
        error('Administrator must configure a Jenkins OIDC role and short-lived token file; no SSO or static-key fallback.')
    }
    withEnv(["AWS_ROLE_ARN=${role}", 'AWS_REGION=us-west-2', 'AWS_DEFAULT_REGION=us-west-2',
             'AWS_EC2_METADATA_DISABLED=true', 'AWS_CONFIG_FILE=/dev/null', 'AWS_SHARED_CREDENTIALS_FILE=/dev/null']) {
        sh 'bash ci/scripts/aws-preflight.sh'
        action()
    }
}

def archiveEvidence() {
    archiveArtifacts artifacts: 'ci-artifacts/**', allowEmptyArchive: true, fingerprint: true
}

return this
