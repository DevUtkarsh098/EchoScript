"""Release-only allow list. Never emit Terraform values or sensitive plan content."""
import hashlib
import json
import sys
from pathlib import Path

ALLOWED = {
    'aws_ecs_express_gateway_service.api': [('update',)],
    'aws_ecs_task_definition.worker': [('create', 'delete'), ('delete', 'create'), ('update',)],
    'aws_sfn_state_machine.transcription': [('update',)],
    'aws_iam_role_policy.state_machine': [('update',)],
}


def summarize(plan):
    if plan.get('errored') or plan.get('deferred_changes'):
        raise ValueError('Incomplete or errored plan')
    changes = []
    for resource in plan.get('resource_changes', []):
        actions = tuple(resource['change']['actions'])
        if resource.get('mode') == 'data' or actions == ('no-op',):
            continue
        address = resource['address']
        if actions not in ALLOWED.get(address, []):
            raise ValueError('Plan contains a change outside the approved application-release scope')
        changes.append({'address': address, 'actions': list(actions)})
    return {'resource_changes': changes, 'scope': 'API/worker image release; no data-resource changes'}


if __name__ == '__main__':
    plan = json.load(sys.stdin)
    summary = summarize(plan)
    summary['plan_sha256'] = hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()
    print(json.dumps(summary, indent=2))
