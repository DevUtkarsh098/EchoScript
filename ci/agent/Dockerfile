FROM hashicorp/terraform:1.14.0 AS terraform
FROM aquasec/trivy:0.76.2 AS trivy
FROM docker:29.0.0-cli AS docker
FROM node:22-bookworm-slim AS node
FROM public.ecr.aws/aws-cli/aws-cli:2.31.26 AS aws
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    age ca-certificates curl git jq openssh-client tar unzip \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 1000 --create-home --shell /bin/bash jenkins
COPY --from=terraform /bin/terraform /usr/local/bin/terraform
COPY --from=trivy /usr/local/bin/trivy /usr/local/bin/trivy
COPY --from=docker /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=aws /usr/local/aws-cli /usr/local/aws-cli
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && ln -s /usr/local/aws-cli/v2/current/bin/aws /usr/local/bin/aws
COPY ci/agent/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY infrastructure/ansible/requirements.yml /tmp/ansible-collections.yml
RUN ansible-galaxy collection install -r /tmp/ansible-collections.yml -p /usr/share/ansible/collections
ENV ANSIBLE_LOCAL_TEMP=/tmp/ansible-local
WORKDIR /workspace
CMD ["bash"]
