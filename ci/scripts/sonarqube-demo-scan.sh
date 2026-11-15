#!/usr/bin/env bash
set -Eeuo pipefail

: "${SONAR_HOST_URL:?Set SONAR_HOST_URL to the private SonarQube URL}"
: "${SONAR_TOKEN:?Provide a project-scoped SonarQube analysis token}"

if ! command -v git >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1 || ! command -v unzip >/dev/null 2>&1; then
  echo "This scan requires git, curl, and unzip." >&2
  exit 2
fi

git fetch --quiet --no-tags origin giri
expected_commit=$(git rev-parse FETCH_HEAD)
current_commit=$(git rev-parse HEAD)
if [[ "$current_commit" != "$expected_commit" ]]; then
  echo "SonarQube Community Build demo scans only the current origin/giri commit." >&2
  exit 2
fi

scanner_version=8.3.1.16491
scanner_url="https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${scanner_version}-linux-x64.zip"
scanner_tmp=$(mktemp -d)
trap 'rm -rf "$scanner_tmp"' EXIT

curl --fail --silent --show-error --location --retry 3 "$scanner_url" -o "$scanner_tmp/scanner.zip"
unzip -q "$scanner_tmp/scanner.zip" -d "$scanner_tmp"
scanner=$(find "$scanner_tmp" -type f -path '*/bin/sonar-scanner' -print -quit)
if [[ -z "$scanner" ]]; then
  echo "The SonarScanner archive did not contain its launcher." >&2
  exit 2
fi

echo "Analyzing EchoScript giri commit $current_commit with SonarQube Community Build."
"$scanner" -Dproject.settings=ci/sonar-project.properties
