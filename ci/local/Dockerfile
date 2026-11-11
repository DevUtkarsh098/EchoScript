# Disposable validation controller ONLY. Production controllers use separate agents.
FROM jenkins/jenkins:lts-jdk21 AS controller
RUN jenkins-plugin-cli --plugins workflow-aggregator git pipeline-stage-view
FROM echoscript-ci-tools:local
COPY --from=controller /opt/java/openjdk /opt/java/openjdk
COPY --from=controller /usr/share/jenkins/jenkins.war /opt/jenkins.war
COPY --from=controller /usr/share/jenkins/ref/plugins /opt/jenkins-plugins
COPY ci/local/init.groovy /opt/echoscript-init.groovy
ENV JAVA_HOME=/opt/java/openjdk JENKINS_HOME=/var/jenkins_home
ENV PATH=/opt/java/openjdk/bin:$PATH
ENTRYPOINT ["bash", "-c", "mkdir -p /var/jenkins_home/plugins /var/jenkins_home/init.groovy.d && cp -n /opt/jenkins-plugins/* /var/jenkins_home/plugins/ && cp /opt/echoscript-init.groovy /var/jenkins_home/init.groovy.d/echoscript.groovy && exec java -Djenkins.install.runSetupWizard=false -Dhudson.plugins.git.GitSCM.ALLOW_LOCAL_CHECKOUT=true -jar /opt/jenkins.war --httpPort=8080"]
