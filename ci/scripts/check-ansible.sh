#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/infrastructure/ansible"
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
ansible-lint --offline
ansible-playbook playbooks/site.yml --syntax-check
ansible-playbook playbooks/jenkins-hosts.yml --syntax-check
# This script runs only INSIDE a fresh disposable Docker container as root.
[[ -f /.dockerenv && "$(id -u)" == 0 ]] || { echo 'Use the disposable Docker target.' >&2; exit 2; }
ansible-playbook playbooks/site.yml --check
ansible-playbook playbooks/site.yml
# Fail if either a second apply or check mode proposes another change.
for mode in apply check; do
  args=()
  [[ "$mode" == check ]] && args+=(--check)
  log="$(mktemp)"
  trap 'rm -f "$log"' EXIT
  ansible-playbook playbooks/site.yml "${args[@]}" | tee "$log"
  grep -Eq 'changed=0[[:space:]]+unreachable=0[[:space:]]+failed=0' "$log"
  rm -f "$log"
done
