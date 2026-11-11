#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p ci-artifacts
TAG="$(git rev-parse HEAD)"
TOOLS_IMAGE="${TOOLS_IMAGE:-echoscript-ci-tools:local}"
TF_DIR=infrastructure/terraform/single-account
case "${1:?validation stage required}" in
  tools)
    git --version; docker --version; node --version; npm --version; python3 --version
    terraform version; trivy --version; aws --version; ansible --version; ansible-lint --version
    ;;
  frontend)
    (cd frontend && npm ci && npm run build)
    ;;
  api)
    docker build --platform linux/amd64 -t "echoscript-api:$TAG" services/ingest-service
    docker run --rm --entrypoint python3.12 "echoscript-api:$TAG" -m pytest -q tests
    ;;
  worker)
    docker build --platform linux/amd64 -t "echoscript-worker:$TAG" services/transcribe-worker
    docker build --build-arg "WORKER_IMAGE=echoscript-worker:$TAG" \
      -f "$ROOT/ci/worker-tests.Dockerfile" -t "echoscript-worker-tests:$TAG" services/transcribe-worker
    docker run --rm "echoscript-worker-tests:$TAG"
    ;;
  terraform)
    terraform fmt -check -recursive "$TF_DIR"
    # PR checks NEVER initialize the production backend or receive AWS credentials.
    TF_DATA_DIR="$ROOT/ci-private/tf-validation" terraform -chdir="$TF_DIR" init -backend=false -input=false -lockfile=readonly
    TF_DATA_DIR="$ROOT/ci-private/tf-validation" terraform -chdir="$TF_DIR" validate
    ;;
  ansible)
    # No Docker socket, AWS files, SSH keys, or production inventory in this target.
    docker build --build-arg "TOOLS_IMAGE=$TOOLS_IMAGE" -f ci/ansible-test.Dockerfile -t "echoscript-ansible-test:$TAG" .
    docker run --rm "echoscript-ansible-test:$TAG"
    ;;
  secrets)
    bash ci/scripts/scan-secrets.sh
    python3 -m unittest discover -s ci/tests -p 'test_*.py'
    ;;
  images)
    docker build --platform linux/amd64 -t "echoscript-frontend:$TAG" frontend
    for component in api worker frontend; do
      trivy image --scanners vuln --ignorefile= --severity HIGH,CRITICAL --exit-code 1 \
        --format json --output "ci-artifacts/trivy-${component}.json" "echoscript-${component}:$TAG"
    done
    ;;
  *) echo 'Unknown validation stage' >&2; exit 2 ;;
esac
