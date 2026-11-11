import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('iam_render', ROOT / 'ci/iam/render.py')
iam = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iam)


class IamTests(unittest.TestCase):
    def setUp(self):
        self.policies = iam.policies(SimpleNamespace(
            state_bucket='confirmed-state-bucket', state_key='echoscript/prod/terraform.tfstate',
            lock_table='confirmed-lock-table', distribution='CONFIRMED-DISTRIBUTION',
            api_service_arn='arn:aws:ecs:us-west-2:598391748654:service/confirmed/api',
            user_pool_arn='arn:aws:cognito-idp:us-west-2:598391748654:userpool/confirmed',
        ))

    def test_publisher_only_pushes_existing_application_repositories(self):
        statements = self.policies['publish']
        self.assertEqual(statements[0]['Action'], ['ecr:GetAuthorizationToken'])
        self.assertEqual(len(statements[1]['Resource']), 2)
        self.assertTrue(all('/echoscript/prod/' in resource for resource in statements[1]['Resource']))
        self.assertNotIn('ecr:CreateRepository', statements[1]['Action'])

    def test_roles_cannot_delete_objects_or_write_application_tables(self):
        for statements in self.policies.values():
            for statement in statements:
                self.assertNotIn('s3:DeleteObject', statement['Action'])
                self.assertNotIn('iam:CreateRole', statement['Action'])
                if 'dynamodb:PutItem' in statement['Action']:
                    self.assertTrue(all(resource.endswith('/confirmed-lock-table') for resource in statement['Resource']))

    def test_plan_role_cannot_publish_images_or_mutate_application_infrastructure(self):
        actions = {action for statement in self.policies['plan'] for action in statement['Action']}
        self.assertNotIn('ecr:PutImage', actions)
        self.assertNotIn('ecs:UpdateExpressGatewayService', actions)
        self.assertNotIn('states:UpdateStateMachine', actions)


if __name__ == '__main__':
    unittest.main()
