#!/usr/bin/env bash
set -euo pipefail

TRIVY_BIN=${TRIVY_BIN:-trivy}
if ! command -v "$TRIVY_BIN" >/dev/null 2>&1; then
  echo "Required secret scanner not found: ${TRIVY_BIN}" >&2
  exit 127
fi

echo "Scanning the checked-out source tree for secrets with Trivy"
# Scanner output can contain matched text or nearby source context. Suppress it
# entirely so findings never enter Jenkins console logs; preserve the exit code.
if "$TRIVY_BIN" fs --scanners secret --secret-config ci/trivy-secret.yaml \
  --ignorefile= --exit-code 1 --format table --quiet . >/dev/null 2>&1; then
  echo "Trivy filesystem secret scan passed"
else
  scan_status=$?
  echo "Trivy filesystem secret scan failed (exit ${scan_status}); scanner output suppressed to protect source content" >&2
  exit "$scan_status"
fi
