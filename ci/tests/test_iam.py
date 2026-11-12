import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

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

    @staticmethod
    def action_statements(statements, action):
        return [statement for statement in statements if action in statement['Action']]

    def test_deploy_inline_policy_mutation_is_limited_and_passrole_stays_scoped(self):
        deploy = self.policies['deploy']
        put = self.action_statements(deploy, 'iam:PutRolePolicy')
        self.assertEqual(len(put), 1)
        self.assertEqual(put[0]['Resource'], ['arn:aws:iam::598391748654:role/echoscript-prod-workflow'])
        pass_roles = self.action_statements(deploy, 'iam:PassRole')
        self.assertEqual(len(pass_roles), 2)
        self.assertTrue(all(statement['Resource'] != ['*'] for statement in pass_roles))
        self.assertTrue(all('iam:PassedToService' in statement['Condition']['StringEquals'] for statement in pass_roles))
        self.assertIn('no policy-name condition', (ROOT / 'ci/iam/render.py').read_text(encoding='utf-8'))

    def test_frontend_role_has_no_state_access_and_limits_s3_objects(self):
        frontend = self.policies['frontend']
        actions = {action for statement in frontend for action in statement['Action']}
        self.assertNotIn('s3:GetObjectVersion', actions)
        self.assertFalse(any('state' in resource for statement in frontend for resource in statement['Resource']))
        listing = self.action_statements(frontend, 's3:ListBucket')
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]['Condition'], {'StringEquals': {'s3:prefix': ''}})
        reads = self.action_statements(frontend, 's3:GetObject')
        self.assertEqual([resource for item in reads for resource in item['Resource']],
                         ['arn:aws:s3:::echoscript-598391748654-prod-web/releases/*'])
        writes = self.action_statements(frontend, 's3:PutObject')
        self.assertEqual(set(writes[0]['Resource']), {
            'arn:aws:s3:::echoscript-598391748654-prod-web/index.html',
            'arn:aws:s3:::echoscript-598391748654-prod-web/assets/*',
            'arn:aws:s3:::echoscript-598391748654-prod-web/releases/*',
        })
        invalidation = self.action_statements(frontend, 'cloudfront:CreateInvalidation')
        self.assertEqual(invalidation[0]['Resource'], ['arn:aws:cloudfront::598391748654:distribution/CONFIRMED-DISTRIBUTION'])

    def test_plan_bucket_reads_and_cloudfront_oac_are_scoped(self):
        plan = self.policies['plan']
        bucket_reads = [statement for statement in plan if any(action.startswith('s3:GetBucket') for action in statement['Action'])]
        bucket_actions = {action for statement in bucket_reads for action in statement['Action']}
        self.assertNotIn('s3:GetBucket*', bucket_actions)
        self.assertIn('s3:GetBucketVersioning', bucket_actions)
        self.assertIn('s3:GetBucketPublicAccessBlock', bucket_actions)
        tags = self.action_statements(plan, 'logs:ListTagsForResource')
        self.assertTrue(all(resource.startswith('arn:aws:logs:us-west-2:598391748654:log-group:')
                            for resource in tags[0]['Resource']))
        oac = self.action_statements(plan, 'cloudfront:GetOriginAccessControl')
        self.assertEqual(oac[0]['Resource'], ['arn:aws:cloudfront::598391748654:origin-access-control/*'])
        lock = next(statement for statement in plan if 'dynamodb:PutItem' in statement['Action'])
        self.assertEqual(lock['Resource'], ['arn:aws:dynamodb:us-west-2:598391748654:table/confirmed-lock-table'])

    def test_no_unexpected_wildcard_permissions_in_generated_policies(self):
        # These APIs do not support resource-level permissions.
        wildcard_actions = {
            'ecr:GetAuthorizationToken', 'ec2:DescribeAvailabilityZones', 'ec2:DescribeVpcs',
            'ec2:DescribeVpcAttribute', 'ec2:DescribeSubnets', 'ec2:DescribeInternetGateways',
            'ec2:DescribeRouteTables', 'ec2:DescribeSecurityGroups', 'ec2:DescribeSecurityGroupRules',
            'ec2:DescribeNetworkAcls', 'lambda:ListEventSourceMappings',
            'logs:DescribeLogGroups',
        }
        for policy_name, statements in self.policies.items():
            for statement in statements:
                if '*' in statement['Resource']:
                    self.assertTrue(set(statement['Action']).issubset(wildcard_actions),
                                    f'unexpected wildcard resource in {policy_name}: {statement}')

    def test_renderer_uses_exact_express_service_arn_and_emits_no_oidc_trust(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            service_arn = 'arn:aws:ecs:us-west-2:598391748654:service/test-cluster/test-api'
            argv = [
                'render.py', '--state-bucket', 'confirmed-state-bucket', '--state-key', 'echoscript/prod/terraform.tfstate',
                '--lock-table', 'confirmed-lock-table', '--distribution', 'E3BEUA9S47DFB2',
                '--api-service-arn', service_arn,
                '--user-pool-arn', 'arn:aws:cognito-idp:us-west-2:598391748654:userpool/us-west-2_hJ5iQgI4j',
                '--output', str(output),
            ]
            with patch.object(sys, 'argv', argv):
                iam.main()
            deploy = json.loads((output / 'deploy.json').read_text())
            update = next(statement for statement in deploy['Statement'] if 'ecs:UpdateExpressGatewayService' in statement['Action'])
            self.assertEqual(update['Resource'], [service_arn])
            self.assertFalse((output / 'trust.json').exists())
            for policy_file in output.glob('*.json'):
                self.assertNotIn('AssumeRoleWithWebIdentity', policy_file.read_text())


if __name__ == '__main__':
    unittest.main()
