#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
[[ -n "${TF_PLAN_RECIPIENT:-}" ]] || exit 0
logs=()
for name in plan.log show.log apply.log; do
  [[ -f "ci-private/$name" ]] && logs+=("$name")
done
if (( ${#logs[@]} )); then
  # Encrypt diagnostics as well; Terraform logs may contain state values.
  tar -czf - -C ci-private "${logs[@]}" | age -r "$TF_PLAN_RECIPIENT" -o ci-artifacts/terraform-logs.tar.gz.age
fi
