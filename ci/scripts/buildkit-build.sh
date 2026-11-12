#!/usr/bin/env bash
set -euo pipefail
: "${BUILDKIT_HOST:?Rootless BuildKit endpoint is required}"
context="${1:?context directory required}"
dockerfile="${2:?Dockerfile required}"
target="${3:-}"
image="${4:-}"
archive="${5:-}"
args=(--addr "$BUILDKIT_HOST" build --frontend dockerfile.v0 --local "context=$context" --local "dockerfile=$(dirname "$dockerfile")" --opt "filename=$(basename "$dockerfile")" --opt platform=linux/amd64)
if [[ -n "$target" ]]; then args+=(--opt "target=$target"); fi
if [[ -n "$image" ]]; then
  [[ -n "$archive" ]] || { echo 'Image output archive is required.' >&2; exit 2; }
  mkdir -p "$(dirname "$archive")"
  args+=(--output "type=docker,name=$image,dest=$archive")
fi
buildctl "${args[@]}"
