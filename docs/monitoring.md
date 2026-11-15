# Local monitoring and alerting

EchoScript's local monitoring profile adds Prometheus scraping and rule evaluation, Alertmanager routing, a provisioned Grafana dashboard, and Mailpit as a local notification inbox. It runs on the Compose network and binds web ports to loopback; it does not provision AWS resources or send alert mail externally.

## Start and open the stack

Copy `.env.example` to `.env`, replace `GRAFANA_ADMIN_PASSWORD` with a unique local password, then run:

```sh
make monitor
```

- Grafana: <http://localhost:3000> (user `admin`, password from `.env`)
- Prometheus: <http://localhost:9090>
- Alertmanager: <http://localhost:9093>
- Mailpit alert inbox: <http://localhost:8025>

Prometheus scrapes the API's `/metrics` endpoint every 15 seconds. Alertmanager emails are captured by Mailpit. To stop the services while preserving local metric and dashboard data, run `make monitor-down`.

## Alerts

The provisioned rules in `monitoring/alerts/application.yml` cover:

- API target unavailable for two minutes (critical).
- API 5xx response ratio above 5% for five minutes (warning).
- API p95 latency above one second for five minutes (warning).
- Local transcription failure ratio above 20% for ten minutes (warning).

The dashboard is provisioned from `monitoring/grafana/dashboards/echoscript.json`. Local thresholds are starting points; tune them against real production traffic before using these rules as production paging thresholds. This profile observes the local Compose API and mock processor. Production AWS/ECS alert delivery needs a separately approved deployment and notification destination.

## AWS-hosted professor demo

The AWS demo runs on the existing Jenkins controller EC2 instance. It does not create another EC2 instance, change security groups, or expose monitoring ports publicly. Prometheus scrapes the existing HTTPS EchoScript API endpoint; the dashboard and AWS alerts use metrics confirmed on that live endpoint.

On the controller, clone the merged `giri` branch into `/opt/echoscript-monitoring`, then create a root-only Grafana password file and start the dedicated AWS Compose stack:

```sh
sudo install -d -m 0700 /etc/echoscript-monitoring
sudo sh -c 'umask 077; printf "GRAFANA_ADMIN_PASSWORD=%s\\n" "$(openssl rand -hex 32)" > /etc/echoscript-monitoring/grafana.env'
cd /opt/echoscript-monitoring
sudo docker compose --env-file /etc/echoscript-monitoring/grafana.env -f docker-compose.aws-monitoring.yml up -d
```

The password stays on the encrypted controller disk and is not committed. Retrieve it through an authenticated SSM shell on the controller with `sudo cat /etc/echoscript-monitoring/grafana.env`. Use the Grafana username `admin`.

Use separate SSM port-forward sessions from your Mac while presenting:

| Service | Mac URL | EC2 port |
|---|---|---:|
| Grafana dashboard and Alertmanager view | <http://localhost:13000> | 3000 |
| Prometheus targets, queries, and firing rules | <http://localhost:19090> | 9090 |
| Alertmanager | <http://localhost:19093> | 9093 |
| Captured demo alert emails | <http://localhost:18025> | 8025 |

For example, map Grafana with:

```sh
aws ssm start-session --profile echoscript-deploy --region us-west-2 --target <JENKINS_CONTROLLER_INSTANCE_ID> --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["3000"],"localPortNumber":["13000"]}'
```

Repeat with the port pairs above for Prometheus, Alertmanager, and Mailpit. Keep each session open while using its URL. All remote listeners bind to EC2 loopback, so do not add inbound security-group rules. `docker compose ... down` stops the demo containers but keeps their named volumes; do not use `down -v` unless intentionally deleting the monitoring history.
