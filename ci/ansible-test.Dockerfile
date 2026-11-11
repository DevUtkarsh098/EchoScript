ARG TOOLS_IMAGE=echoscript-ci-tools:local
FROM ${TOOLS_IMAGE}
COPY infrastructure/ansible /workspace/infrastructure/ansible
COPY ci/scripts/check-ansible.sh /workspace/ci/scripts/check-ansible.sh
CMD ["bash", "ci/scripts/check-ansible.sh"]
