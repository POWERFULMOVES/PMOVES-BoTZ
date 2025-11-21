# Metrics & Alerting

## Built-in overlay
- Compose file: `features/metrics/docker-compose.yml`
- Prometheus: `http://localhost:${PROMETHEUS_PORT:-9090}`
- Grafana: `http://localhost:${GRAFANA_PORT:-3033}`
- Alertmanager: `http://localhost:${ALERTMANAGER_PORT:-9093}`

### Prometheus
- Config: `features/metrics/prometheus.yml`
- Rules: `features/metrics/prometheus.rules.yml`
- Scrapes:
  - `mcp-gateway:8000/metrics`
  - `docling-mcp:3020/metrics`
  - Blackbox probes via `host.docker.internal:9115`

### Alertmanager
- Config template: `features/metrics/alertmanager.tmpl.yml`
- Env vars (set in `.env` or shell):
  - `SLACK_WEBHOOK_URL`, `SLACK_CHANNEL` (default `#alerts`)
  - `DISCORD_WEBHOOK_URL`
  - `GRAFANA_BASE_URL` (default uses `${GRAFANA_PORT}`)
- Routes messages to Slack and to the Discord adapter container.

### Grafana
- Datasources (provisioned):
  - `pmz-prom` → internal Prometheus
  - `host-prom` → `http://host.docker.internal:9090` (your existing prometheus-1)
- Dashboards (provisioned):
  - `PMOVES Overview` (uid: `pmoves-overview`)
  - `PMOVES Services Health` (uid: `pmoves-health`)

## Using existing grafana-1 (3002)
- PowerShell:
```
./scripts/grafana_provision.ps1 -GrafanaUrl http://localhost:3002 -PromUrl http://host.docker.internal:9090
```
- Bash:
```
./scripts/grafana_provision.sh GRAFANA_URL=http://localhost:3002 PROM_URL=http://host.docker.internal:9090
```

## Slack & Discord
- Slack: create an Incoming Webhook and set `SLACK_WEBHOOK_URL`. Channel defaults to `#alerts` or set `SLACK_CHANNEL`.
- Discord: create a webhook in the target channel and set `DISCORD_WEBHOOK_URL`.

Alerts include a Grafana link to `pmoves-health`: `${GRAFANA_BASE_URL}/d/pmoves-health/pmoves-services-health`.

