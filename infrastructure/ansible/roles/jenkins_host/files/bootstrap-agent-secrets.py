#!/usr/bin/env python3
"""Idempotently capture JCasC-created inbound node tokens into role secrets."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import ssl
import time


def secret_from_jnlp(payload: bytes) -> str:
    root = ET.fromstring(payload)
    arguments = [element.text or '' for element in root.iter('argument')]
    for index, value in enumerate(arguments[:-1]):
        if value in ('-secret', '-jnlpCredentials'):
            token = arguments[index + 1]
            if re.fullmatch(r'[A-Za-z0-9_-]{32,}', token):
                return token
    # Recent Jenkins versions return the node token as the first JNLP
    # argument without a -secret flag. Accept only an unambiguous token.
    candidates = [value for value in arguments if re.fullmatch(r'[A-Za-z0-9_-]{32,}', value)]
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError('Jenkins agent JNLP response did not contain a valid node secret')


def merge_agent_bootstrap(payload: dict, token: str, ca_pem: str) -> dict:
    """Retain role fixtures and make retries stable for the same token and CA."""
    return {**payload, 'agent_secret': token, 'controller_ca_pem': ca_pem}


def aws_secret(secret_id: str, region: str) -> dict:
    result = subprocess.run(
        ['aws', 'secretsmanager', 'get-secret-value', '--secret-id', secret_id,
         '--region', region, '--query', 'SecretString', '--output', 'text'],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        if 'ResourceNotFoundException' in result.stderr:
            return {}
        raise RuntimeError(f'Unable to read bootstrap payload for {secret_id}') from None
    try:
        value = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        raise RuntimeError(f'Invalid JSON bootstrap payload for {secret_id}') from None
    if not isinstance(value, dict):
        raise RuntimeError(f'Bootstrap payload for {secret_id} must be a JSON object')
    return value


def write_secret(secret_id: str, region: str, value: dict, workdir: Path) -> bool:
    path = workdir / (secret_id.rsplit('/', 1)[-1] + '.json')
    path.write_text(json.dumps(value, separators=(',', ':'), sort_keys=True), encoding='utf-8')
    path.chmod(0o600)
    result = subprocess.run(
        ['aws', 'secretsmanager', 'put-secret-value', '--secret-id', secret_id,
         '--region', region, '--secret-string', f'file://{path}', '--query', 'VersionId', '--output', 'text'],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(f'Unable to update bootstrap payload for {secret_id}') from None
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--ca-file', type=Path, required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--region', required=True)
    parser.add_argument('--verify-online', action='store_true')
    parser.add_argument('--nodes', default='validation,release')
    args = parser.parse_args()

    env = {}
    for line in args.env_file.read_text(encoding='utf-8').splitlines():
        key, separator, value = line.partition('=')
        if separator:
            env[key] = value
    user = env.get('JENKINS_ADMIN_ID', '')
    password = env.get('JENKINS_ADMIN_PASSWORD', '')
    if not user or not password:
        raise RuntimeError('Controller administrator credentials are missing')

    ca_pem = args.ca_file.read_text(encoding='ascii')
    tls = ssl.create_default_context(cafile=str(args.ca_file))
    auth = base64.b64encode(f'{user}:{password}'.encode('utf-8')).decode('ascii')
    if args.verify_online:
        for _ in range(40):
            request = urllib.request.Request(
                f"{args.url.rstrip('/')}/computer/api/json?tree=computer[displayName,offline]",
                headers={'Authorization': f'Basic {auth}'},
            )
            try:
                with urllib.request.urlopen(request, context=tls, timeout=20) as response:
                    computers = json.loads(response.read()).get('computer', [])
                online = {item.get('displayName') for item in computers if not item.get('offline')}
                if {'echoscript-validation', 'echoscript-release'} <= online:
                    print('both Jenkins agents are online with trusted TLS')
                    return
            except (urllib.error.URLError, ValueError):
                pass
            time.sleep(15)
        raise RuntimeError('Timed out waiting for both Jenkins agents to connect')
    changed = False
    selected_nodes = {node.strip() for node in args.nodes.split(',') if node.strip()}
    if not selected_nodes or not selected_nodes <= {'validation', 'release'}:
        raise RuntimeError('Requested agent bootstrap roles are invalid')
    with tempfile.TemporaryDirectory(prefix='jenkins-agent-secrets-', dir='/run') as temp:
        workdir = Path(temp)
        os.chmod(workdir, 0o700)
        node_secrets = {
            'validation': ('echoscript-validation', 'echoscript/jenkins/validation/bootstrap'),
            'release': ('echoscript-release', 'echoscript/jenkins/release/bootstrap'),
        }
        for role in ('validation', 'release'):
            if role not in selected_nodes:
                continue
            node_name, secret_id = node_secrets[role]
            # Avoid encrypted JNLP mode: it requires the unknown secret to decrypt.
            url = f"{args.url.rstrip('/')}/computer/{node_name}/jenkins-agent.jnlp"
            request = urllib.request.Request(url, headers={'Authorization': f'Basic {auth}'})
            try:
                with urllib.request.urlopen(request, context=tls, timeout=20) as response:
                    token = secret_from_jnlp(response.read())
            except (urllib.error.URLError, ValueError, ET.ParseError):
                raise RuntimeError(f'Unable to obtain the configured token for {node_name}') from None

            payload = aws_secret(secret_id, args.region)
            if node_name == 'echoscript-release':
                if not re.fullmatch(r'[A-Za-z0-9_.-]{16,}', str(payload.get('smoke_token', ''))):
                    raise RuntimeError('Release bootstrap payload requires the approved smoke_token')
                if not re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', str(payload.get('smoke_audio_base64', ''))):
                    raise RuntimeError('Release bootstrap payload requires smoke_audio_base64')
            updated = merge_agent_bootstrap(payload, token, ca_pem)
            if payload != updated:
                write_secret(secret_id, args.region, updated, workdir)
                changed = True
    print('agent bootstrap values updated' if changed else 'agent bootstrap values already current')


if __name__ == '__main__':
    main()
