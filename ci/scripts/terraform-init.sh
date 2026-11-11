#!/usr/bin/env bash
set +x
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
source ci/scripts/aws-preflight.sh
: "${TF_BACKEND_FILE:?Administrator must mount the existing backend configuration}"
: "${TF_STATE_BUCKET:?Existing state bucket must be confirmed by the administrator}"
: "${TF_STATE_KEY:?Existing state key must be confirmed by the administrator}"
: "${TF_LOCK_TABLE:?Existing lock table must be confirmed by the administrator}"
[[ "${TF_WORKSPACE:-default}" == default ]] || { echo 'Only the existing default workspace is supported.' >&2; exit 2; }
python3 ci/scripts/backend_guard.py
# Confirm the object already exists. NEVER bootstrap, migrate, or create empty state.
aws s3api head-object --bucket "$TF_STATE_BUCKET" --key "$TF_STATE_KEY" --expected-bucket-owner 598391748654 >/dev/null
[[ "$(aws s3api get-bucket-location --bucket "$TF_STATE_BUCKET" --expected-bucket-owner 598391748654 --query LocationConstraint --output text)" == us-west-2 ]]
export TF_DATA_DIR="$ROOT/ci-private/tf-release"
mkdir -p "$TF_DATA_DIR"
terraform -chdir=infrastructure/terraform/single-account init -input=false -lockfile=readonly -backend-config="$TF_BACKEND_FILE"
