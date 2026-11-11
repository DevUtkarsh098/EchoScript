#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT/infrastructure/terraform/single-account"
REGION="${AWS_REGION:-us-west-2}"
TAG="${1:-}"

cd "$ROOT"

if [[ -z "$TAG" ]]; then
  echo "Pass the committed Git SHA to publish, for example: scripts/publish-images.sh YOUR_GIT_SHA" >&2
  exit 2
fi

if [[ ! "$TAG" =~ ^[a-f0-9]{7,40}$ ]]; then
  echo "Image tag must be a hexadecimal Git commit SHA." >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to publish from a dirty checkout; commit or remove all source changes first." >&2
  exit 2
fi
if [[ "$(git rev-parse "$TAG^{commit}" 2>/dev/null || true)" != "$(git rev-parse HEAD)" ]]; then
  echo "The image tag must identify the current checked-out commit." >&2
  exit 2
fi
EXPECTED_ACCOUNT="$(terraform -chdir="$TF_DIR" output -raw account_id)" || {
  echo "Existing Terraform outputs are unavailable. Initialize the confirmed existing backend; do not recreate repositories." >&2
  exit 2
}
if [[ "$EXPECTED_ACCOUNT" != 598391748654 || "$REGION" != us-west-2 ]]; then
  echo "Refusing to publish outside the existing account 598391748654/us-west-2." >&2
  exit 3
fi
IDENTITY="$(aws sts get-caller-identity --output json)"
ACTIVE_ACCOUNT="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["Account"])' <<< "$IDENTITY")"
if [[ "$ACTIVE_ACCOUNT" != "$EXPECTED_ACCOUNT" ]]; then
  echo "Refusing to publish: active AWS account does not match this Terraform state." >&2
  exit 3
fi
if [[ "$REGION" != "$(terraform -chdir="$TF_DIR" output -raw region)" ]]; then
  echo "Refusing to publish: AWS_REGION does not match the Terraform region." >&2
  exit 3
fi

API_REPOSITORY="$(terraform -chdir="$TF_DIR" output -raw api_image_repository)"
WORKER_REPOSITORY="$(terraform -chdir="$TF_DIR" output -raw worker_image_repository)"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${EXPECTED_ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
docker build --platform linux/amd64 -f "$ROOT/services/ingest-service/Dockerfile" -t "$API_REPOSITORY:$TAG" "$ROOT/services/ingest-service"
docker build --platform linux/amd64 -f "$ROOT/services/transcribe-worker/Dockerfile" -t "$WORKER_REPOSITORY:$TAG" "$ROOT/services/transcribe-worker"
bash "$ROOT/ci/scripts/scan-secrets.sh"
if ! command -v trivy >/dev/null 2>&1; then
  echo "Required Trivy image scanner is missing; refusing to publish images." >&2
  exit 127
fi
trivy image --exit-code 1 --severity HIGH,CRITICAL "$API_REPOSITORY:$TAG"
trivy image --exit-code 1 --severity HIGH,CRITICAL "$WORKER_REPOSITORY:$TAG"
docker push "$API_REPOSITORY:$TAG"
docker push "$WORKER_REPOSITORY:$TAG"
echo "Published immutable image tag $TAG to the Terraform-selected account in $REGION."
