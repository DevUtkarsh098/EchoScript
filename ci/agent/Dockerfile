FROM hashicorp/terraform:1.14.0 AS terraform
FROM aquasec/trivy:0.76.2 AS trivy
FROM moby/buildkit:v0.34.1-rootless AS buildkit
FROM node:22-bookworm-slim AS node
FROM public.ecr.aws/aws-cli/aws-cli:2.31.26 AS aws
FROM jenkins/inbound-agent:jdk21

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    age ca-certificates curl git jq openssh-client tar unzip python3 python3-venv python3-pip skopeo \
    && rm -rf /var/lib/apt/lists/* \
    && install -d -o jenkins -g jenkins /opt/ci-venv
COPY --from=terraform /bin/terraform /usr/local/bin/terraform
COPY --from=trivy /usr/local/bin/trivy /usr/local/bin/trivy
COPY --from=buildkit /usr/bin/buildctl /usr/local/bin/buildctl
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=aws /usr/local/aws-cli /usr/local/aws-cli
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && ln -s /usr/local/aws-cli/v2/current/bin/aws /usr/local/bin/aws
COPY ci/agent/requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/ci-venv \
    && /opt/ci-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
COPY infrastructure/ansible/requirements.yml /tmp/ansible-collections.yml
RUN /opt/ci-venv/bin/ansible-galaxy collection install -r /tmp/ansible-collections.yml -p /usr/share/ansible/collections
ENV ANSIBLE_LOCAL_TEMP=/tmp/ansible-local
ENV PATH="/opt/ci-venv/bin:${PATH}"
COPY ci/agent/entrypoint.sh /usr/local/bin/echoscript-agent-entrypoint
RUN chmod 0755 /usr/local/bin/echoscript-agent-entrypoint
WORKDIR /workspace
USER jenkins
ENTRYPOINT ["/usr/local/bin/echoscript-agent-entrypoint"]
