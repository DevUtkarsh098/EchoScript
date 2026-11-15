# SonarQube Community Build demo on AWS

This is an isolated, free Community Build demo for the EchoScript **giri** branch. It adds a dedicated SonarQube EC2 host; it does not change ECS/Fargate application deployment or the Jenkins controller.

## What it provides

- SonarQube Community Build **26.11.0.134175-community** with persistent Docker volumes on an encrypted 40 GiB gp3 root disk.
- A dedicated **t3a.large** host with the SSM instance profile already used by the validation agent.
- TCP 9000 allowed only from the existing validation-agent security group. No public inbound rule is added.
- Browser access through an SSM port-forward to local port 19000.
- A separately configured single-branch Jenkins job in **ci/Jenkinsfile.sonar**, plus the EchoScript source configuration in **ci/sonar-project.properties**.

The Community Build is intended for a demo here. It uses its built-in H2 database; this is not a production database design. The existing EchoScript-PR multibranch job remains unchanged. Community Build does not support analysis from Jenkins multibranch jobs or general branch analysis, so this demo scans only the current giri branch. SonarQube analysis complements Trivy and npm audit; it does not replace them.

## Deploy the AWS host

The stack uses the existing project VPC, subnet, validation-agent security group, and SSM instance profile. The SonarQube web UI remains private; the host public IPv4 is used only for outbound downloads, and no public ingress is opened.

~~~bash
aws cloudformation create-stack \
  --profile echoscript-deploy \
  --region us-west-2 \
  --stack-name echoscript-sonarqube-demo \
  --template-url https://raw.githubusercontent.com/DevUtkarsh098/EchoScript/codex/add-sonarqube-aws-demo/infrastructure/cloudformation/sonarqube-demo.yml \
  --parameters \
    ParameterKey=VpcId,ParameterValue=vpc-0314dbfef4e6363f3 \
    ParameterKey=SubnetId,ParameterValue=subnet-06ca9db3f0802b67c \
    ParameterKey=ValidationAgentSecurityGroupId,ParameterValue=sg-02c25bf669e92100c \
    ParameterKey=SSMInstanceProfileName,ParameterValue=echoscript-jenkins-validation-host \
    ParameterKey=SourceRef,ParameterValue=codex/add-sonarqube-aws-demo
~~~

Wait until the stack is CREATE_COMPLETE and its EC2 instance appears as a managed node in Systems Manager. Cloud-init installs Docker and Compose, applies the Elasticsearch host limits, then starts SonarQube. First startup can take several minutes.

The t3a.large compute list price in us-west-2 is about **$54.90/month** if it runs continuously (730 hours). EBS storage, the public IPv4 address, data transfer, taxes, and any CPU-credit overage are additional. Stop the EC2 instance between demonstrations to reduce compute cost; its EBS disk continues to incur storage charges while stopped. The account budget is $220/month, so review actual spend after deployment.

## Open SonarQube privately

Use the instance ID from the CloudFormation stack output:

~~~bash
aws ssm start-session \
  --profile echoscript-deploy \
  --region us-west-2 \
  --target <SONARQUBE_INSTANCE_ID> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["9000"],"localPortNumber":["19000"]}'
~~~

Leave that Terminal window open and visit http://localhost:19000. The first-login credentials are admin / admin; change the password immediately. Create a project with key echoscript, then create a **project analysis** token for that project. Do not commit or paste the token into source files or build logs.

## Configure the single-branch Jenkins analysis job

1. In Jenkins, add the generated token as a **Secret text** credential with ID sonarqube-demo-token.
2. Set the Jenkins global environment variable SONAR_HOST_URL to http://<SONARQUBE_PRIVATE_IP>:9000 using the private IP from the stack output.
3. Create a regular **Pipeline** job (not Multibranch) named EchoScript-Sonar-Giri, using this repository, branch giri, and script path ci/Jenkinsfile.sonar.
4. Run the job manually. It verifies the checkout is exactly the current origin/giri head before sending source analysis. The project appears in SonarQube after the first successful scan.

Keep the token in Jenkins credentials. Do not expose it to pull-request builds. The SonarQube Community Build cannot analyze pull requests or the existing multibranch job; those features require a paid Server edition.

## Lifecycle

- Stop/start the EC2 instance with the AWS console or aws ec2 stop-instances / start-instances. Docker restarts SonarQube automatically after boot.
- The SonarQube database and analysis history are on the EC2 root disk and survive an instance stop/start.
- Deleting the CloudFormation stack terminates the demo host and deletes its root disk and SonarQube history.
