import io
import os
from pathlib import Path
import subprocess
import shutil
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(shutil.which('age') and shutil.which('age-keygen'), 'age/age-keygen are required for encrypted archive integration test')
class ProtectedLogTests(unittest.TestCase):
    def test_diagnostics_are_encrypted_and_not_printed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / 'operations-key'
            subprocess.run(['age-keygen', '-o', str(key)], check=True, capture_output=True)
            recipient = subprocess.run(['age-keygen', '-y', str(key)], check=True, capture_output=True, text=True).stdout.strip()
            private = root / 'ci-private'
            private.mkdir()
            marker = 'PRIVATE-PLAN-TEST-MARKER'
            (private / 'plan.log').write_text(marker)
            artifacts = root / 'ci-artifacts'
            artifacts.mkdir()
            env = dict(os.environ, TF_PLAN_RECIPIENT=recipient)
            result = subprocess.run(['bash', str(ROOT / 'ci/scripts/archive-private-logs.sh')],
                                    cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(marker, result.stdout + result.stderr)
            archive = artifacts / 'terraform-logs.tar.gz.age'
            self.assertNotIn(marker.encode(), archive.read_bytes())
            decrypted = subprocess.run(['age', '--decrypt', '-i', str(key), str(archive)], check=True, capture_output=True).stdout
            with tarfile.open(fileobj=io.BytesIO(decrypted), mode='r:gz') as logs:
                self.assertEqual(logs.extractfile('plan.log').read().decode(), marker)


if __name__ == '__main__':
    unittest.main()
