#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
mkdir -p ci-artifacts
TAG="$(git rev-parse HEAD)"
IMAGE_DIR="${IMAGE_DIR:-$ROOT/ci-private/images}"
mkdir -p "$IMAGE_DIR"
TF_DIR=infrastructure/terraform/single-account
case "${1:?validation stage required}" in
  tools)
    git --version; buildctl --version; skopeo --version; node --version; npm --version; python3 --version
    terraform version; trivy --version; aws --version; ansible --version; ansible-lint --version
    ;;
  frontend)
    (cd frontend && npm ci && npm run build && npm test -- --run \
      && npm audit --audit-level=high --json > "$ROOT/ci-artifacts/npm-audit.json")
    ;;
  api)
    bash ci/scripts/buildkit-build.sh services/ingest-service services/ingest-service/Dockerfile ci-test
    ;;
  worker)
    bash ci/scripts/buildkit-build.sh services/transcribe-worker services/transcribe-worker/Dockerfile ci-test
    ;;
  terraform)
    # PR checks NEVER initialize the production backend or receive AWS credentials.
    for directory in "$TF_DIR" infrastructure/terraform/jenkins-hosting; do
      terraform fmt -check -recursive "$directory"
      export TF_DATA_DIR="$ROOT/ci-private/tf-validation/$(basename "$directory")"
      terraform -chdir="$directory" init -backend=false -input=false -lockfile=readonly
      terraform -chdir="$directory" validate
    done
    ;;
  ansible)
    # No Docker socket, AWS files, SSH keys, or production inventory in this target.
    buildctl --addr "$BUILDKIT_HOST" build --frontend dockerfile.v0 --local context=. --local dockerfile=. \
      --opt filename=ci/ansible-test.Dockerfile
    ;;
  secrets)
    bash ci/scripts/scan-secrets.sh
    python3 -m unittest discover -s ci/tests -p 'test_*.py'
    ;;
  images)
    bash ci/scripts/buildkit-build.sh frontend frontend/Dockerfile '' "echoscript-frontend:$TAG" "$IMAGE_DIR/frontend.tar"
    bash ci/scripts/buildkit-build.sh services/ingest-service services/ingest-service/Dockerfile '' \
      "echoscript-api:$TAG" "$IMAGE_DIR/api.tar"
    bash ci/scripts/buildkit-build.sh services/transcribe-worker services/transcribe-worker/Dockerfile '' \
      "echoscript-worker:$TAG" "$IMAGE_DIR/worker.tar"
    # Static bundles do not retain package-lock metadata in the runtime image.
    # Scan the locked JS dependency graph too, including build/test tools.
    trivy fs --scanners vuln --include-dev-deps --ignorefile= --severity HIGH,CRITICAL --exit-code 1 \
      --skip-dirs frontend/node_modules --skip-dirs frontend/dist --format json \
      --output ci-artifacts/trivy-frontend-dependencies.json frontend
    for component in api worker frontend; do
      trivy image --scanners vuln --ignorefile= --severity HIGH,CRITICAL --exit-code 1 \
        --format json --output "ci-artifacts/trivy-${component}.json" --input "$IMAGE_DIR/${component}.tar"
    done
    ;;
  *) echo 'Unknown validation stage' >&2; exit 2 ;;
esac
