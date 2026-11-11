import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('machine_profile', ROOT / 'ci/scripts/machine_profile.py')
machine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(machine)


class MachineProfileTests(unittest.TestCase):
    def text(self):
        return '\n'.join(f'''[profile jenkins-{role}]
role_arn=arn:aws:iam::598391748654:role/echoscript-jenkins-{role}
credential_source=Ec2InstanceMetadata
region=us-west-2
duration_seconds=900
''' for role in machine.ROLES)

    def test_fixed_machine_role_profile(self):
        machine.validate(self.text(), 'jenkins-plan', 'arn:aws:iam::598391748654:role/echoscript-jenkins-plan')

    def test_sso_and_static_profile_fields_rejected(self):
        for suffix in ['sso_session=another-developer', 'aws_access_key_id=local-test-marker', 'source_profile=default']:
            with self.assertRaises(ValueError):
                machine.validate(self.text() + suffix, 'jenkins-plan', 'arn:aws:iam::598391748654:role/echoscript-jenkins-plan')

    def test_wrong_account_or_profile_rejected(self):
        with self.assertRaises(ValueError):
            machine.validate(self.text(), 'default', 'arn:aws:iam::598391748654:role/echoscript-jenkins-plan')
        with self.assertRaises(ValueError):
            machine.validate(self.text().replace('598391748654', '111111111111'), 'jenkins-plan', 'arn:aws:iam::598391748654:role/echoscript-jenkins-plan')
