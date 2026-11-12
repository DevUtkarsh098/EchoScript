#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
[[ "${IMAGE_TAG:-}" =~ ^[a-f0-9]{40}$ ]] || { echo 'A full immutable commit SHA is required.' >&2; exit 2; }
REGISTRY=598391748654.dkr.ecr.us-west-2.amazonaws.com
case "${1:?release command required}" in
  verify-tag) ;;
  verify-images)
    source ci/scripts/aws-preflight.sh
    export AUTH_FILE="$ROOT/ci-private/skopeo-auth.json"
    mkdir -p "$ROOT/ci-private"; chmod 700 "$ROOT/ci-private"
    trap 'rm -f "$AUTH_FILE"' EXIT
    aws ecr get-login-password --region us-west-2 | skopeo login --authfile "$AUTH_FILE" --username AWS --password-stdin "$REGISTRY" >/dev/null 2>&1
    for name in ingest-service transcribe-worker; do
      aws ecr describe-images --repository-name "echoscript/prod/$name" --image-ids "imageTag=$IMAGE_TAG" \
        --query 'imageDetails[0].imageDigest' --output text > /dev/null
      skopeo copy --authfile "$AUTH_FILE" "docker://$REGISTRY/echoscript/prod/$name:$IMAGE_TAG" \
        "docker-archive:$ROOT/ci-private/rollback-$name.tar:$name:$IMAGE_TAG"
      trivy image --scanners vuln --ignorefile= --severity HIGH,CRITICAL --exit-code 1 \
        --format json --output "ci-artifacts/trivy-target-$name.json" --input "$ROOT/ci-private/rollback-$name.tar"
    done
    ;;
  publish)
    source ci/scripts/aws-preflight.sh
    [[ "$IMAGE_TAG" == "$(git rev-parse HEAD)" ]]
    [[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo 'Commit source changes before publishing.' >&2; exit 2; }
    export AUTH_FILE="$ROOT/ci-private/skopeo-auth.json"
    mkdir -p "$ROOT/ci-private"; chmod 700 "$ROOT/ci-private"
    trap 'rm -f "$AUTH_FILE"' EXIT
    aws ecr get-login-password --region us-west-2 | skopeo login --authfile "$AUTH_FILE" --username AWS --password-stdin "$REGISTRY" >/dev/null 2>&1
    for component in api worker; do
      if [[ "$component" == api ]]; then name=ingest-service; else name=transcribe-worker; fi
      repository="echoscript/prod/$name"
      # Never create repositories or overwrite immutable tags.
      [[ "$(aws ecr describe-repositories --repository-names "$repository" --query 'repositories[0].imageTagMutability' --output text)" == IMMUTABLE ]]
      archive="$ROOT/ci-private/images/$component.tar"
      [[ -s "$archive" ]] || { echo "Scanned image archive is missing for $component." >&2; exit 1; }
      # Scan the EXACT local image that will be tagged/pushed; no rebuild after gates.
      trivy image --scanners vuln --ignorefile= --severity HIGH,CRITICAL --exit-code 1 \
        --format json --output "ci-artifacts/trivy-publish-$component.json" --input "$archive"
      skopeo copy --authfile "$AUTH_FILE" "docker-archive:$archive:echoscript-$component:$IMAGE_TAG" \
        "docker://$REGISTRY/$repository:$IMAGE_TAG"
      aws ecr describe-images --repository-name "$repository" --image-ids "imageTag=$IMAGE_TAG" \
        --query 'imageDetails[0].{tag:imageTags,digest:imageDigest}' --output json > "ci-artifacts/published-$component.json"
    done
    ;;
  apply)
    source ci/scripts/aws-preflight.sh
    export TF_DATA_DIR="$ROOT/ci-private/tf-release"
    sha256sum --check --status ci-private/release.tfplan.sha256
    # Saved plan only: no replanning, -target, state migration, destroy, or data cleanup.
    terraform -chdir=infrastructure/terraform/single-account apply -input=false -lock-timeout=5m \
      "$ROOT/ci-private/release.tfplan" > ci-private/apply.log 2>&1 || {
      echo 'Apply failed. Do not automatically retry or roll back Terraform; inspect restricted logs.' >&2; exit 1;
    }
    printf '{"apply":"succeeded","image_tag":"%s"}\n' "$IMAGE_TAG" > ci-artifacts/apply-result.json
    ;;
  *) echo 'Unknown release command' >&2; exit 2 ;;
esac
