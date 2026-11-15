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
