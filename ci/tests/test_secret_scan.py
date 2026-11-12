import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ci" / "scripts" / "scan-secrets.sh"


@unittest.skipUnless(os.name != 'nt', 'Bash shell integration tests require a POSIX runner')
class SecretScanTests(unittest.TestCase):
    def run_scan(self, scanner_exit):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scanner = tmp_path / "fake-trivy.sh"
            args_file = tmp_path / "args.txt"
            scanner.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' \"$@\" > \"$TRIVY_ARGS_FILE\"\n"
                "printf '%s\\n' 'SENSITIVE-TEST-MARKER'\n"
                "printf '%s\\n' 'SENSITIVE-TEST-MARKER' >&2\n"
                "exit \"$FAKE_TRIVY_EXIT\"\n",
                encoding="utf-8",
            )
            scanner.chmod(0o755)
            env = os.environ.copy()
            env.update(
                TRIVY_BIN=str(scanner),
                TRIVY_ARGS_FILE=str(args_file),
                FAKE_TRIVY_EXIT=str(scanner_exit),
            )
            result = subprocess.run(
                ["bash", str(SCRIPT)], cwd=ROOT, env=env, capture_output=True, text=True
            )
            return result, args_file.read_text(encoding="utf-8").splitlines()

    def test_invokes_secret_scan_and_passes_clean_exit(self):
        result, args = self.run_scan(0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            args,
            [
                "fs",
                "--scanners",
                "secret",
                "--secret-config",
                "ci/trivy-secret.yaml",
                "--ignorefile=",
                "--exit-code",
                "1",
                "--format",
                "table",
                "--quiet",
                ".",
            ],
        )

    def test_secret_finding_blocks_pipeline(self):
        result, _ = self.run_scan(1)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("SENSITIVE-TEST-MARKER", result.stdout)
        self.assertNotIn("SENSITIVE-TEST-MARKER", result.stderr)
        self.assertIn("output suppressed", result.stderr)

    def test_scanner_error_fails_pipeline(self):
        result, _ = self.run_scan(2)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("SENSITIVE-TEST-MARKER", result.stdout)
        self.assertNotIn("SENSITIVE-TEST-MARKER", result.stderr)

    def test_missing_scanner_fails_closed(self):
        env = os.environ.copy()
        env["TRIVY_BIN"] = "scanner-that-does-not-exist"
        result = subprocess.run(
            ["bash", str(SCRIPT)], cwd=ROOT, env=env, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 127)
        self.assertIn("Required secret scanner not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
