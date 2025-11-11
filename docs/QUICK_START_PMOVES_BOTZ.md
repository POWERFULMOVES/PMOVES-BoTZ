# PMOVES‑BotZ Quick Start

## Option A: Standalone (Local‑First with Ollama)

1) Local‑first bootstrap (.env auto‑created at repo root)

- The bring‑up scripts read `.env` from the repo root.
- If `.env` is missing, `scripts/bring_up_pmoves_botz.(ps1|sh)` will auto‑create it from `core/example.env` and feature examples, so you don’t have to cd into subfolders.
- Defaults bias to local‑first:
  - `VL_PROVIDER=ollama`
  - `OLLAMA_BASE_URL=http://host.docker.internal:11434`

2) Namespace and ports (PowerShell example)

```
$env:PMZ_NAMESPACE='botz-dev'
$env:COMPOSE_PROJECT_NAME=$env:PMZ_NAMESPACE
$env:PMOVES_AI_NETWORK='pmoves-net'
$env:GATEWAY_PORT='22091'; $env:DOCLING_PORT='23020'; $env:E2B_PORT='17071'; $env:VL_PORT='17072'
$env:PROMETHEUS_PORT='29090'; $env:GRAFANA_PORT='23033'; $env:ALERTMANAGER_PORT='29093'
```

3) Rebuild Docling and bring up the stack:

```
docker compose --env-file .env -f core/docker-compose/base.yml build --no-cache docling-mcp

docker compose --env-file .env `
  -f core/docker-compose/base.yml `
  -f features/pro/docker-compose.yml `
  -f features/network/external.yml `
  -f features/metrics/docker-compose.yml `
  up -d
```

4) Slack/Discord alerts (optional)

Set in environment or .env:
- `SLACK_WEBHOOK_URL` and optional `SLACK_CHANNEL` (default `#alerts`)
- `DISCORD_WEBHOOK_URL`
- `GRAFANA_BASE_URL` (default uses `${GRAFANA_PORT}`)

## Option B: BYO Monitoring (use existing prometheus-1/grafana-1)

1) Start PMOVES‑BotZ core + pro + pmoves‑net:

```
docker compose --env-file .env `
  -f core/docker-compose/base.yml `
  -f features/pro/docker-compose.yml `
  -f features/network/external.yml `
  up -d
```

2) Provision your grafana‑1 (port 3002) with our dashboards:

```
# PowerShell
./scripts/grafana_provision.ps1 -GrafanaUrl http://localhost:3002 -PromUrl http://host.docker.internal:9090

# Bash
./scripts/grafana_provision.sh GRAFANA_URL=http://localhost:3002 PROM_URL=http://host.docker.internal:9090
```

## Health URLs
- Gateway: `http://localhost:${GATEWAY_PORT}/ready`, `/metrics`
- Docling: `http://localhost:${DOCLING_PORT}/health`, `/metrics`
- Prometheus: `http://localhost:${PROMETHEUS_PORT}/targets`
- Grafana: `http://localhost:${GRAFANA_PORT}/`
- Alertmanager: `http://localhost:${ALERTMANAGER_PORT}/`

## Internal DNS (pmoves-net)
- Gateway: `http://mcp-gateway:8000`
- Docling: `http://docling-mcp:3020`
- E2B: `http://e2b-runner:7071`  |  VL: `http://vl-sentinel:7072`
- Cipher (optional): `http://cipher-memory:3011`

## Kilo‑Bots: “Mini Transformers Team”
- The Kilo‑Bots (Gateway, Docling, VL, E2B, Cipher) work like a mini transformers squad — each specialized, stronger together.
- Autodiscovery labels (`pmoves.service`, `pmoves.health`) let new bots self‑publish; Prometheus picks them up via file_sd.
- Local‑first by default: use your host Ollama as the visual‑language backbone; cloud providers are optional add‑ons.
