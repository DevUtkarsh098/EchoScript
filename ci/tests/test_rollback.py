"""Exercise the actual frontend rollback script using local AWS/Terraform doubles."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SHA = 'a' * 40


class RollbackTests(unittest.TestCase):
    def test_previous_bundle_is_restored_and_unrelated_objects_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in ['scripts/deploy-frontend.sh', 'ci/scripts/aws-preflight.sh', 'ci/scripts/bundle.py']:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, path)
            (root / 'infrastructure/terraform/single-account').mkdir(parents=True)
            binaries = root / 'bin'
            binaries.mkdir()
            cloud = root / 'mock-cloud'
            releases = cloud / 'releases' / SHA
            releases.mkdir(parents=True)
            archive = releases / 'frontend.tar.gz'
            with tarfile.open(archive, 'w:gz') as capsule:
                data = b'<html>previous immutable bundle</html>'
                entry = tarfile.TarInfo('index.html')
                entry.size = len(data)
                capsule.addfile(entry, io.BytesIO(data))
            (releases / 'frontend.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest())
            (cloud / 'unrelated-object').write_text('preserve')
            (cloud / 'index.html').write_text('new release')
            token = root / 'oidc-token'
            token.write_text('local-test-double')
            aws = binaries / 'aws'
            aws.write_text('''#!/usr/bin/env python3
import json,os,sys,shutil
from pathlib import Path
a=sys.argv[1:]; cloud=Path(os.environ['MOCK_CLOUD'])
if a[:2]==['sts','get-caller-identity']:
 print(json.dumps({'Account':'598391748654','Arn':'arn:aws:sts::598391748654:assumed-role/echoscript-jenkins-frontend/test'}))
elif a[:2]==['s3','cp']:
 def local(value):
  return cloud / value.split('/',3)[3] if value.startswith('s3://') else Path(value)
 source,target=map(local,a[2:4]); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
elif a[:2]==['s3','sync']:
 assert '--delete' not in a
 source=Path(a[2])
 for path in source.rglob('*'):
  if path.is_file() and path.name != 'index.html':
   target=cloud/path.relative_to(source); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)
elif a[:2]==['cloudfront','create-invalidation']: print('TEST-INVALIDATION')
elif a[:2]==['cloudfront','wait']: pass
else: raise SystemExit('Unexpected AWS operation in rollback test')
''')
            aws.chmod(0o755)
            terraform = binaries / 'terraform'
            outputs = {'account_id': '598391748654', 'region': 'us-west-2',
                       'frontend_bucket': 'echoscript-598391748654-prod-web',
                       'frontend_url': 'https://dtdd5d335m3k2.cloudfront.net',
                       'frontend_distribution_id': 'TEST-DISTRIBUTION'}
            terraform.write_text('#!/usr/bin/env python3\nimport sys\nprint(' + repr(outputs) + '[sys.argv[-1]])\n')
            terraform.chmod(0o755)
            env = {key: value for key, value in os.environ.items() if not key.startswith('AWS_')}
            env.update(PATH=str(binaries) + os.pathsep + env['PATH'], MOCK_CLOUD=str(cloud),
                       AWS_REGION='us-west-2', AWS_DEFAULT_REGION='us-west-2',
                       AWS_ROLE_ARN='arn:aws:iam::598391748654:role/echoscript-jenkins-frontend',
                       AWS_WEB_IDENTITY_TOKEN_FILE=str(token))
            for operation in ['prepare-rollback', 'rollback']:
                result = subprocess.run(['bash', 'scripts/deploy-frontend.sh', operation, SHA], cwd=root,
                                        env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((cloud / 'index.html').read_bytes(), data)
            self.assertEqual((cloud / 'unrelated-object').read_text(), 'preserve')
            evidence = json.loads((root / 'ci-artifacts/frontend-result.json').read_text())
            self.assertEqual(evidence['release'], SHA)
            self.assertEqual(evidence['mode'], 'rollback')


if __name__ == '__main__':
    unittest.main()
