#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT/infrastructure/terraform/single-account"
REGION="${AWS_REGION:-us-west-2}"

cd "$ROOT"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to publish from a dirty checkout; commit or remove all source changes first." >&2
  exit 2
fi

EXPECTED_ACCOUNT="$(terraform -chdir="$TF_DIR" output -raw account_id)" || {
  echo "Terraform outputs are unavailable; deploy the approved infrastructure first." >&2
  exit 2
}
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

API_URL="$(terraform -chdir="$TF_DIR" output -raw api_url)"
COGNITO_DOMAIN="$(terraform -chdir="$TF_DIR" output -raw cognito_domain)"
COGNITO_CLIENT_ID="$(terraform -chdir="$TF_DIR" output -raw cognito_client_id)"
FRONTEND_URL="$(terraform -chdir="$TF_DIR" output -raw frontend_url)"
FRONTEND_BUCKET="$(terraform -chdir="$TF_DIR" output -raw frontend_bucket)"
CLOUDFRONT_ID="$(terraform -chdir="$TF_DIR" output -raw frontend_distribution_id)"

cd "$ROOT/frontend"
VITE_APP_ENV=production VITE_MOCK_AUTH=false VITE_API_URL="$API_URL" \
  VITE_COGNITO_DOMAIN="$COGNITO_DOMAIN" VITE_COGNITO_CLIENT_ID="$COGNITO_CLIENT_ID" \
  VITE_COGNITO_REDIRECT_URI="$FRONTEND_URL/auth/callback" npm run build
aws s3 sync dist/ "s3://$FRONTEND_BUCKET/" --delete --region "$REGION" --cache-control "public,max-age=300"
aws cloudfront create-invalidation --distribution-id "$CLOUDFRONT_ID" --paths '/*' >/dev/null
echo "Published the production frontend to $FRONTEND_URL."
