"""Render reviewable IAM policies only. This tool NEVER calls AWS or creates roles.

Use confirmed live resource metadata; do not infer or bootstrap a new backend.
"""
import argparse
import json
from pathlib import Path

ACCOUNT = '598391748654'
REGION = 'us-west-2'
def statement(actions, resources, condition=None):
    value = {'Effect': 'Allow', 'Action': actions, 'Resource': resources}
    if condition:
        value['Condition'] = condition
    return value


def policies(args):
    regional = {'StringEquals': {'aws:RequestedRegion': REGION}}
    state_bucket = f'arn:aws:s3:::{args.state_bucket}'
    state = [
        statement(['s3:ListBucket', 's3:GetBucketLocation'], [state_bucket]),
        statement(['s3:GetObject'], [f'{state_bucket}/{args.state_key}']),
    ]
    lock = statement(['dynamodb:DescribeTable', 'dynamodb:GetItem', 'dynamodb:PutItem', 'dynamodb:DeleteItem'],
                     [f'arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/{args.lock_table}'], regional)
    ecr = [f'arn:aws:ecr:{REGION}:{ACCOUNT}:repository/echoscript/prod/{name}' for name in ('ingest-service', 'transcribe-worker')]
    web = f'arn:aws:s3:::echoscript-{ACCOUNT}-prod-web'
    cf = f'arn:aws:cloudfront::{ACCOUNT}:distribution/{args.distribution}'
    workflow = f'arn:aws:states:{REGION}:{ACCOUNT}:stateMachine:echoscript-prod-transcription'
    roles = [f'arn:aws:iam::{ACCOUNT}:role/echoscript-prod-*']
    read = [
        statement(['ecr:GetAuthorizationToken'], ['*'], regional),
        statement(['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer', 'ecr:BatchCheckLayerAvailability'], ecr, regional),
        statement(['ec2:DescribeAvailabilityZones', 'ec2:DescribeVpcs', 'ec2:DescribeVpcAttribute', 'ec2:DescribeSubnets',
                   'ec2:DescribeInternetGateways', 'ec2:DescribeRouteTables', 'ec2:DescribeSecurityGroups',
                   'ec2:DescribeSecurityGroupRules', 'ec2:DescribeNetworkAcls'], ['*'], regional),
        statement(['ecs:DescribeExpressGatewayService', 'ecs:DescribeTaskDefinition', 'ecs:DescribeClusters', 'ecs:ListTagsForResource'],
                  [args.api_service_arn, f'arn:aws:ecs:{REGION}:{ACCOUNT}:task-definition/echoscript-prod-transcribe-worker:*',
                   f'arn:aws:ecs:{REGION}:{ACCOUNT}:cluster/echoscript-prod-workers'], regional),
        statement(['ecr:DescribeRepositories', 'ecr:DescribeImages', 'ecr:GetLifecyclePolicy', 'ecr:ListTagsForResource'], ecr, regional),
        statement(['iam:GetRole', 'iam:GetRolePolicy', 'iam:ListRolePolicies', 'iam:ListAttachedRolePolicies'], roles),
        # Terraform refreshes only these configured bucket controls. Keep object
        # listing out of the application bucket reads; state listing is scoped above.
        statement(['s3:GetBucketLocation', 's3:GetBucketVersioning', 's3:GetEncryptionConfiguration',
                   's3:GetBucketPublicAccessBlock', 's3:GetBucketOwnershipControls', 's3:GetBucketCORS',
                   's3:GetBucketTagging'],
                  [f'arn:aws:s3:::echoscript-{ACCOUNT}-prod-{kind}' for kind in ('input', 'output', 'web')]),
        statement(['s3:GetLifecycleConfiguration'],
                  [f'arn:aws:s3:::echoscript-{ACCOUNT}-prod-{kind}' for kind in ('input', 'output')]),
        statement(['s3:GetBucketPolicy'], [web]),
        statement(['s3:GetObject'], [f'{web}/releases/*']),
        statement(['dynamodb:DescribeTable', 'dynamodb:DescribeContinuousBackups', 'dynamodb:DescribeTimeToLive', 'dynamodb:ListTagsOfResource'],
                  [f'arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/echoscript-prod-*'], regional),
        statement(['dynamodb:GetItem'], [f'arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/echoscript-prod-worker-slots'], regional),
        statement(['sqs:GetQueueAttributes', 'sqs:ListQueueTags'], [f'arn:aws:sqs:{REGION}:{ACCOUNT}:echoscript-prod-*'], regional),
        statement(['lambda:GetFunction', 'lambda:GetFunctionCodeSigningConfig', 'lambda:GetPolicy', 'lambda:ListTags'],
                  [f'arn:aws:lambda:{REGION}:{ACCOUNT}:function:echoscript-prod-*'], regional),
        statement(['lambda:GetEventSourceMapping'], [f'arn:aws:lambda:{REGION}:{ACCOUNT}:event-source-mapping:*'], regional),
        statement(['lambda:ListEventSourceMappings'], ['*'], regional),
        statement(['states:DescribeStateMachine', 'states:ListTagsForResource'], [workflow], regional),
        statement(['logs:DescribeLogGroups'], ['*'], regional),
        statement(['logs:ListTagsForResource'], [
            f'arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/ecs/echoscript-prod-*',
            f'arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/aws/lambda/echoscript-prod-*',
        ], regional),
        statement(['cloudfront:GetDistribution', 'cloudfront:GetDistributionConfig', 'cloudfront:ListTagsForResource'], [cf]),
        # OAC IDs are not a renderer input, so scope to the OAC resource type
        # in this account rather than all CloudFront resource types.
        statement(['cloudfront:GetOriginAccessControl'], [f'arn:aws:cloudfront::{ACCOUNT}:origin-access-control/*']),
        statement(['cognito-idp:DescribeUserPool', 'cognito-idp:DescribeUserPoolClient', 'cognito-idp:DescribeUserPoolDomain',
                   'cognito-idp:ListTagsForResource'], [args.user_pool_arn], regional),
        statement(['budgets:ViewBudget'], [f'arn:aws:budgets::{ACCOUNT}:budget/*']),
    ]
    deploy = [
        statement(['s3:PutObject'], [f'{state_bucket}/{args.state_key}']),
        statement(['ecs:UpdateExpressGatewayService'], [args.api_service_arn], regional),
        # Registration supports task-definition resource scoping; allow revisions
        # only for the existing worker family.
        statement(['ecs:RegisterTaskDefinition'],
                  [f'arn:aws:ecs:{REGION}:{ACCOUNT}:task-definition/echoscript-prod-transcribe-worker:*'], regional),
        statement(['ecs:DeregisterTaskDefinition', 'ecs:TagResource'],
                  [f'arn:aws:ecs:{REGION}:{ACCOUNT}:task-definition/echoscript-prod-transcribe-worker:*'], regional),
        statement(['states:UpdateStateMachine'], [workflow], regional),
        # Required today: orchestration.tf's state_machine inline policy embeds
        # the versioned worker task-definition ARN and changes on worker release.
        # PutRolePolicy has no policy-name condition, so this grants replacement
        # of any inline policy on this one role. Prefer stable task-family scoping
        # or an admin-owned policy update path to remove this release permission.
        statement(['iam:PutRolePolicy'], [f'arn:aws:iam::{ACCOUNT}:role/echoscript-prod-workflow']),
        statement(['iam:PassRole'], [f'arn:aws:iam::{ACCOUNT}:role/echoscript-prod-{suffix}' for suffix in
                  ('api-execution', 'api-task', 'api-express-infrastructure', 'worker-execution', 'worker-task')],
                  {'StringEquals': {'iam:PassedToService': ['ecs.amazonaws.com', 'ecs-tasks.amazonaws.com']}}),
        statement(['iam:PassRole'], [f'arn:aws:iam::{ACCOUNT}:role/echoscript-prod-workflow'],
                  {'StringEquals': {'iam:PassedToService': 'states.amazonaws.com'}}),
    ]
    return {
        'publish': [statement(['ecr:GetAuthorizationToken'], ['*'], regional),
                    statement(['ecr:DescribeRepositories', 'ecr:DescribeImages', 'ecr:BatchCheckLayerAvailability',
                               'ecr:InitiateLayerUpload', 'ecr:UploadLayerPart', 'ecr:CompleteLayerUpload', 'ecr:PutImage'], ecr, regional)],
        'plan': state + [lock] + read,
        'deploy': state + [lock] + read + deploy,
        'frontend': [
                            # aws s3 sync to the bucket root lists with prefix="";
                            # this is the narrowest compatible ListBucket scope.
                            statement(['s3:ListBucket'], [web], {'StringEquals': {'s3:prefix': ''}}),
                            statement(['s3:GetObject'], [f'{web}/releases/*']),
                            statement(['s3:PutObject'], [f'{web}/index.html', f'{web}/assets/*', f'{web}/releases/*']),
                            statement(['cloudfront:CreateInvalidation', 'cloudfront:GetInvalidation'], [cf])],
        'smoke': [statement(['states:DescribeExecution'],
                           [f'arn:aws:states:{REGION}:{ACCOUNT}:execution:echoscript-prod-transcription:*'], regional)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('state-bucket', 'state-key', 'lock-table', 'distribution', 'api-service-arn', 'user-pool-arn'):
        parser.add_argument('--' + flag, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for value in vars(args).values():
        if isinstance(value, str) and ('*' in value or '?' in value or 'REPLACE' in value):
            parser.error('Supply exact, confirmed metadata and trust claims without wildcards')
    assert args.api_service_arn.startswith(f'arn:aws:ecs:{REGION}:{ACCOUNT}:service/')
    assert args.user_pool_arn.startswith(f'arn:aws:cognito-idp:{REGION}:{ACCOUNT}:userpool/')
    args.output.mkdir(parents=True, exist_ok=True)
    for name, statements in policies(args).items():
        (args.output / f'{name}.json').write_text(json.dumps({'Version': '2012-10-17', 'Statement': statements}, indent=2))


if __name__ == '__main__':
    main()
