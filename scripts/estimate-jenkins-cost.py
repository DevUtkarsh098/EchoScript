"""Reproduce planning arithmetic only. Never calls AWS or authorizes spending."""
import json
from pathlib import Path

data = json.loads((Path(__file__).resolve().parents[1] / 'ci/jenkins-cost-estimate.json').read_text())
agent_hours = data['validation_hours'] + data['release_hours']
fixed = data['ebs_gb'] * data['ebs_gb_month_assumption'] + sum(data[key] for key in (
    'backup_storage_allowance', 's3_backup_storage_allowance', 'logging_allowance', 'secrets_allowance',
    'ecr_storage_allowance', 's3_transfer_allowance', 'network_transfer_allowance'))
nominal = (data['controller_hours'] * data['controller_hourly'] + agent_hours * data['agent_hourly']
           + (data['controller_hours'] + agent_hours) * data['public_ipv4_hourly'] + fixed)
always_on = (730 * data['controller_hourly'] + 1460 * data['agent_hourly']
             + 2190 * data['public_ipv4_hourly'] + fixed)
print(json.dumps({
    'currency': 'USD', 'nominal_jenkins_monthly': round(nominal, 2),
    'planned_jenkins_range': data['jenkins_monthly_range'],
    'combined_account_range': [data['jenkins_monthly_range'][index] + data['existing_application_monthly_estimate'][index] for index in (0, 1)],
    'all_three_hosts_always_on_monthly': round(always_on, 2),
    'cost_approved': data['approved'],
}, indent=2))
