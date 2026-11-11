import jenkins.model.Jenkins
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.plugins.git.GitSCM
import hudson.plugins.git.BranchSpec
import hudson.plugins.git.UserRemoteConfig
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition

def instance = Jenkins.get()
def realm = new HudsonPrivateSecurityRealm(false)
realm.createAccount('local-ci', new File('/run/secrets/local_password').text.trim())
instance.setSecurityRealm(realm)
def authorization = new FullControlOnceLoggedInAuthorizationStrategy()
authorization.setAllowAnonymousRead(false)
instance.setAuthorizationStrategy(authorization)
instance.setNumExecutors(1)
instance.setLabelString('echoscript-validation')
def job = instance.getItem('echoscript-validation') ?: instance.createProject(WorkflowJob, 'echoscript-validation')
def scm = new GitSCM([new UserRemoteConfig('file:///source', null, null, null)], [new BranchSpec('*/giri')], false, [], null, null, [])
job.setDefinition(new CpsScmFlowDefinition(scm, 'ci/Jenkinsfile.validation'))
job.save()
instance.save()
