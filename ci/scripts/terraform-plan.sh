#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
bash ci/scripts/release.sh verify-tag
bash ci/scripts/terraform-init.sh
bash ci/scripts/release.sh verify-images
: "${TF_VAR_FILE:?Mount the existing approved production variable file}"
: "${TF_PLAN_RECIPIENT:?Set the operations public age recipient}"
export TF_DATA_DIR="$ROOT/ci-private/tf-release"
mkdir -p ci-artifacts ci-private
# No raw plan output reaches the console or public Jenkins artifacts.
terraform -chdir=infrastructure/terraform/single-account plan -input=false -lock-timeout=5m \
  -var-file="$TF_VAR_FILE" -var="image_tag=$IMAGE_TAG" -out="$ROOT/ci-private/release.tfplan" > ci-private/plan.log 2>&1 || {
  echo 'Terraform plan failed; restricted workspace log available to the operator.' >&2; exit 1;
}
terraform -chdir=infrastructure/terraform/single-account show -json "$ROOT/ci-private/release.tfplan" 2> ci-private/show.log \
  | python3 ci/scripts/plan_guard.py ci-private/release.tfplan > ci-artifacts/plan-summary.json
age -r "$TF_PLAN_RECIPIENT" -o ci-artifacts/release.tfplan.age ci-private/release.tfplan
sha256sum ci-private/release.tfplan > ci-private/release.tfplan.sha256
echo 'Saved plan encrypted and archived with a value-free release summary; explicit approval is required.'
