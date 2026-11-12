FROM python:3.12-slim
WORKDIR /workspace
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 jenkins && useradd --uid 1000 --gid 1000 --create-home jenkins
COPY ci/agent/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY infrastructure/ansible/requirements.yml /tmp/ansible-collections.yml
RUN ansible-galaxy collection install -r /tmp/ansible-collections.yml -p /usr/share/ansible/collections
COPY infrastructure/ansible /workspace/infrastructure/ansible
COPY ci/scripts/check-ansible.sh /workspace/ci/scripts/check-ansible.sh
RUN CI_ISOLATED_TEST=1 bash ci/scripts/check-ansible.sh
