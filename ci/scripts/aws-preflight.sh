#!/usr/bin/env bash
set +x
set -euo pipefail
[[ "${AWS_REGION:-}" == us-west-2 && "${AWS_DEFAULT_REGION:-}" == us-west-2 ]] || { echo 'Wrong AWS region.' >&2; exit 2; }
[[ -z "${AWS_ACCESS_KEY_ID:-}${AWS_SECRET_ACCESS_KEY:-}${AWS_SESSION_TOKEN:-}" ]] || {
  echo 'Injected AWS keys and developer sessions are prohibited.' >&2; exit 2;
}
[[ "${AWS_ROLE_ARN:-}" =~ ^arn:aws:iam::598391748654:role/echoscript-jenkins-(publish|plan|deploy|frontend|smoke)$ ]] || {
  echo 'An approved Jenkins role in account 598391748654 is required.' >&2; exit 2;
}
export AWS_SHARED_CREDENTIALS_FILE=/dev/null
case "${AWS_JENKINS_CREDENTIAL_MODE:-oidc}" in
  oidc)
    [[ -z "${AWS_PROFILE:-}" && -r "${AWS_WEB_IDENTITY_TOKEN_FILE:?OIDC token file is required}" ]] || exit 2
    unset AWS_PROFILE
    export AWS_CONFIG_FILE=/dev/null AWS_EC2_METADATA_DISABLED=true
    ;;
  ec2-instance-profile)
    export AWS_CONFIG_FILE=/etc/echoscript/aws/config AWS_EC2_METADATA_DISABLED=false
    unset AWS_WEB_IDENTITY_TOKEN_FILE AWS_EC2_METADATA_SERVICE_ENDPOINT AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE
    python3 "$(dirname "${BASH_SOURCE[0]}")/machine_profile.py"
    ;;
  *) echo 'Unapproved Jenkins credential mode.' >&2; exit 2 ;;
esac
# Retired jobs must not inject migration/target/destroy flags into this release.
for option_var in ${!TF_CLI_ARGS@}; do unset "$option_var"; done
unset TF_REATTACH_PROVIDERS
identity="$(aws sts get-caller-identity --output json)"
python3 -c 'import json,os,sys
x=json.load(sys.stdin)
role=os.environ["AWS_ROLE_ARN"].rsplit("/",1)[1]
if x["Account"] != "598391748654": raise SystemExit("Wrong AWS account")
if not x["Arn"].startswith("arn:aws:sts::598391748654:assumed-role/"+role+"/"): raise SystemExit("Wrong AWS role")
print("Verified Jenkins assumed role in account 598391748654, us-west-2")' <<< "$identity"
