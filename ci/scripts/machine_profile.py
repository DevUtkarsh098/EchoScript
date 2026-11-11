"""Allow only fixed, root-managed EC2 role-assumption profiles; never developer SSO."""
import configparser
import os
from pathlib import Path
import stat

ROLES = ('publish', 'plan', 'deploy', 'frontend', 'smoke')


def validate(text, profile, role_arn):
    expected = 'jenkins-' + role_arn.rsplit('/', 1)[1].removeprefix('echoscript-jenkins-')
    if profile != expected:
        raise ValueError('Unexpected Jenkins machine profile')
    config = configparser.ConfigParser(interpolation=None)
    config.read_string(text)
    if config.defaults() or set(config.sections()) != {f'profile jenkins-{role}' for role in ROLES}:
        raise ValueError('Only the five approved machine profiles are allowed')
    for role in ROLES:
        required = {
            'role_arn': f'arn:aws:iam::598391748654:role/echoscript-jenkins-{role}',
            'credential_source': 'Ec2InstanceMetadata',
            'region': 'us-west-2',
            'duration_seconds': '900',
        }
        if dict(config[f'profile jenkins-{role}']) != required:
            raise ValueError('Machine profile must use EC2 metadata and scoped 15-minute roles only')


if __name__ == '__main__':
    path = Path('/etc/echoscript/aws/config')
    metadata = path.stat()
    if path.resolve() != path or metadata.st_uid != 0 or stat.S_IMODE(metadata.st_mode) & 0o022:
        raise SystemExit('Machine config must be root-owned and not writable by builds')
    validate(path.read_text(), os.environ['AWS_PROFILE'], os.environ['AWS_ROLE_ARN'])
