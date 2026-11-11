#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:?prepare|prepare-rollback|deploy|rollback required}"
TAG="${2:?Full immutable release SHA required}"
[[ "$TAG" =~ ^[a-f0-9]{40}$ ]] || exit 2
bash ci/scripts/aws-preflight.sh
export TF_DATA_DIR="$ROOT/ci-private/tf-release"
TF_DIR="$ROOT/infrastructure/terraform/single-account"
output() { terraform -chdir="$TF_DIR" output -raw "$1"; }
[[ "$(output account_id)" == 598391748654 && "$(output region)" == us-west-2 ]]
BUCKET="$(output frontend_bucket)"
[[ "$BUCKET" == echoscript-598391748654-prod-web ]]
FRONTEND_URL="$(output frontend_url)"
[[ "$FRONTEND_URL" == https://dtdd5d335m3k2.cloudfront.net ]]
BASE="$ROOT/ci-private/frontend-$TAG"
ARCHIVE="$BASE.tar.gz"
CHECKSUM="$BASE.sha256"
mkdir -p ci-private ci-artifacts
case "$MODE" in
  prepare)
    [[ "$TAG" == "$(git rev-parse HEAD)" ]]
    API_URL="$(output api_url)"
    [[ "$API_URL" == https://ec-4762c5d9c1fa4c50a19bed3b76373799.ecs.us-west-2.on.aws ]]
    COGNITO_DOMAIN="$(output cognito_domain)"
    COGNITO_CLIENT_ID="$(output cognito_client_id)"
    (cd frontend && VITE_APP_ENV=production VITE_MOCK_AUTH=false VITE_API_URL="$API_URL" \
      VITE_COGNITO_DOMAIN="$COGNITO_DOMAIN" VITE_COGNITO_CLIENT_ID="$COGNITO_CLIENT_ID" \
      VITE_COGNITO_REDIRECT_URI="$FRONTEND_URL/auth/callback" npm run build)
    tar -czf "$ARCHIVE" -C frontend/dist .
    sha256sum "$ARCHIVE" | cut -d' ' -f1 > "$CHECKSUM"
    ;;
  prepare-rollback)
    # Retrieve an existing release; do not rebuild old source with today's packages.
    aws s3 cp "s3://$BUCKET/releases/$TAG/frontend.tar.gz" "$ARCHIVE" --only-show-errors
    aws s3 cp "s3://$BUCKET/releases/$TAG/frontend.sha256" "$CHECKSUM" --only-show-errors
    ;;
  deploy|rollback)
    [[ -s "$ARCHIVE" && -s "$CHECKSUM" ]]
    expected="$(cat "$CHECKSUM")"
    [[ "$expected" =~ ^[a-f0-9]{64}$ && "$expected" == "$(sha256sum "$ARCHIVE" | cut -d' ' -f1)" ]]
    python3 ci/scripts/bundle.py "$ARCHIVE" "$BASE"
    if [[ "$MODE" == deploy ]]; then
      # Conditional writes preserve existing bundles even if a release is retried.
      aws s3api put-object --bucket "$BUCKET" --key "releases/$TAG/frontend.tar.gz" --body "$ARCHIVE" --if-none-match '*' >/dev/null
      aws s3api put-object --bucket "$BUCKET" --key "releases/$TAG/frontend.sha256" --body "$CHECKSUM" --if-none-match '*' >/dev/null
    fi
    # Keep previous hashed assets. Publish index last; NEVER sync --delete.
    aws s3 sync "$BASE/" "s3://$BUCKET/" --exclude index.html --cache-control 'public,max-age=31536000,immutable' --only-show-errors
    aws s3 cp "$BASE/index.html" "s3://$BUCKET/index.html" --cache-control 'no-cache' --content-type text/html --only-show-errors
    distribution="$(output frontend_distribution_id)"
    invalidation="$(aws cloudfront create-invalidation --distribution-id "$distribution" --paths '/*' --query Invalidation.Id --output text)"
    aws cloudfront wait invalidation-completed --distribution-id "$distribution" --id "$invalidation"
    printf '{"frontend":"%s","release":"%s","bundle_sha256":"%s","mode":"%s"}\n' "$FRONTEND_URL" "$TAG" "$expected" "$MODE" > ci-artifacts/frontend-result.json
    ;;
  *) echo 'Unknown frontend release mode' >&2; exit 2 ;;
esac
