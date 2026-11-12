#!/usr/bin/env bash
set -euo pipefail

ca_file=/run/jenkins/jenkins-ca.crt
truststore=/tmp/echoscript-agent-cacerts
if [[ ! -r "$ca_file" ]]; then
  echo 'Controller CA trust file is missing' >&2
  exit 1
fi
cp "$JAVA_HOME/lib/security/cacerts" "$truststore"
keytool -importcert -noprompt -trustcacerts -alias echoscript-controller-ca \
  -file "$ca_file" -keystore "$truststore" -storepass changeit >/dev/null
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-} -Djavax.net.ssl.trustStore=$truststore -Djavax.net.ssl.trustStorePassword=changeit"
exec /usr/local/bin/jenkins-agent "$@"
