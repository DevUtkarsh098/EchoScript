"""Render reviewable IAM policies only. This tool NEVER calls AWS or creates roles.

Use confirmed live resource metadata; do not infer or bootstrap a new backend.
"""
import argparse
import json
from pathlib import Path

ACCOUNT = '598391748654'
REGION = 'us-west-2'
ARN = f'arn:aws'


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
        statement(['s3:GetBucket*', 's3:GetEncryptionConfiguration', 's3:GetLifecycleConfiguration', 's3:ListBucket'],
                  [f'arn:aws:s3:::echoscript-{ACCOUNT}-prod-{kind}' for kind in ('input', 'output', 'web')]),
        statement(['s3:GetObject'], [f'{web}/releases/*']),
        statement(['dynamodb:DescribeTable', 'dynamodb:DescribeContinuousBackups', 'dynamodb:DescribeTimeToLive', 'dynamodb:ListTagsOfResource'],
                  [f'arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/echoscript-prod-*'], regional),
        statement(['dynamodb:GetItem'], [f'arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/echoscript-prod-worker-slots'], regional),
        statement(['sqs:GetQueueAttributes', 'sqs:ListQueueTags'], [f'arn:aws:sqs:{REGION}:{ACCOUNT}:echoscript-prod-*'], regional),
        statement(['lambda:GetFunction', 'lambda:GetFunctionCodeSigningConfig', 'lambda:GetPolicy', 'lambda:ListTags'],
                  [f'arn:aws:lambda:{REGION}:{ACCOUNT}:function:echoscript-prod-*'], regional),
        statement(['lambda:GetEventSourceMapping', 'lambda:ListEventSourceMappings'], ['*'], regional),
        statement(['states:DescribeStateMachine', 'states:ListTagsForResource'], [workflow], regional),
        statement(['logs:DescribeLogGroups', 'logs:ListTagsForResource'], ['*'], regional),
        statement(['cloudfront:GetDistribution', 'cloudfront:GetDistributionConfig', 'cloudfront:ListTagsForResource'], [cf]),
        statement(['cloudfront:GetOriginAccessControl'], ['*']),
        statement(['cognito-idp:DescribeUserPool', 'cognito-idp:DescribeUserPoolClient', 'cognito-idp:DescribeUserPoolDomain',
                   'cognito-idp:ListTagsForResource'], [args.user_pool_arn], regional),
        statement(['budgets:ViewBudget'], [f'arn:aws:budgets::{ACCOUNT}:budget/*']),
    ]
    deploy = [
        statement(['s3:PutObject'], [f'{state_bucket}/{args.state_key}']),
        statement(['ecs:UpdateExpressGatewayService'], [args.api_service_arn], regional),
        # ECS RegisterTaskDefinition has no existing resource ARN; constrain the family
        # through the reviewed saved plan and a dedicated trusted release job.
        statement(['ecs:RegisterTaskDefinition'], ['*'], regional),
        statement(['ecs:DeregisterTaskDefinition', 'ecs:TagResource'],
                  [f'arn:aws:ecs:{REGION}:{ACCOUNT}:task-definition/echoscript-prod-transcribe-worker:*'], regional),
        statement(['states:UpdateStateMachine'], [workflow], regional),
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
        'frontend': state + [statement(['s3:ListBucket'], [web]),
                            statement(['s3:GetObject', 's3:PutObject'], [f'{web}/*']),
                            statement(['cloudfront:CreateInvalidation', 'cloudfront:GetInvalidation'], [cf])],
        'smoke': [statement(['states:DescribeExecution'],
                           [f'arn:aws:states:{REGION}:{ACCOUNT}:execution:echoscript-prod-transcription:*'], regional)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('state-bucket', 'state-key', 'lock-table', 'distribution', 'api-service-arn', 'user-pool-arn', 'oidc-issuer', 'oidc-audience', 'oidc-subject'):
        parser.add_argument('--' + flag, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for value in vars(args).values():
        if isinstance(value, str) and ('*' in value or '?' in value or 'REPLACE' in value):
            parser.error('Supply exact, confirmed metadata and trust claims without wildcards')
    assert args.api_service_arn.startswith(f'arn:aws:ecs:{REGION}:{ACCOUNT}:service/')
    assert args.user_pool_arn.startswith(f'arn:aws:cognito-idp:{REGION}:{ACCOUNT}:userpool/')
    issuer = args.oidc_issuer.removeprefix('https://').rstrip('/')
    args.output.mkdir(parents=True, exist_ok=True)
    for name, statements in policies(args).items():
        (args.output / f'{name}.json').write_text(json.dumps({'Version': '2012-10-17', 'Statement': statements}, indent=2))
    trust = {'Version': '2012-10-17', 'Statement': [{
        'Effect': 'Allow', 'Principal': {'Federated': f'arn:aws:iam::{ACCOUNT}:oidc-provider/{issuer}'},
        'Action': 'sts:AssumeRoleWithWebIdentity',
        'Condition': {'StringEquals': {f'{issuer}:aud': args.oidc_audience, f'{issuer}:sub': args.oidc_subject}},
    }]}
    (args.output / 'trust.json').write_text(json.dumps(trust, indent=2))


if __name__ == '__main__':
    main()
