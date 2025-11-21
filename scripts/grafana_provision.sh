#!/usr/bin/env bash
set -euo pipefail

# Provision an existing Grafana via HTTP API (no container changes needed).
# Defaults assume Grafana on localhost:3002 and admin/admin creds.

GRAFANA_URL=${GRAFANA_URL:-http://localhost:3002}
GRAFANA_USER=${GRAFANA_USER:-admin}
GRAFANA_PASS=${GRAFANA_PASS:-admin}

# Data source to host Prometheus (your existing prometheus-1 on 9090)
PROM_URL=${PROM_URL:-http://host.docker.internal:9090}

auth() {
  curl -sS -u "$GRAFANA_USER:$GRAFANA_PASS" "$@"
}

echo "Creating Prometheus datasource 'host-prom' at $PROM_URL ..."
auth -H 'Content-Type: application/json' \
  -X POST "$GRAFANA_URL/api/datasources" \
  -d '{
    "name": "host-prom",
    "type": "prometheus",
    "access": "proxy",
    "url": "'"$PROM_URL"'",
    "isDefault": false
  }' || true

echo "Importing PMOVES Overview dashboard ..."
DASH_JSON_PATH="$(cd "$(dirname "$0")/.." && pwd)/features/metrics/grafana/dashboards/pmoves_overview.json"

# Import dashboard, mapping the input datasource to host-prom
auth -H 'Content-Type: application/json' \
  -X POST "$GRAFANA_URL/api/dashboards/import" \
  -d @- <<JSON || true
{
  "dashboard": $(cat "$DASH_JSON_PATH"),
  "overwrite": true,
  "inputs": [
    {"name": "__DS_PROM__", "type": "datasource", "pluginId": "prometheus", "value": "host-prom"}
  ],
  "folderId": 0
}
JSON

echo "Importing PMOVES Services Health dashboard ..."
HEALTH_JSON_PATH="$(cd "$(dirname "$0")/.." && pwd)/features/metrics/grafana/dashboards/pmoves_services_health.json"
auth -H 'Content-Type: application/json' \
  -X POST "$GRAFANA_URL/api/dashboards/import" \
  -d @- <<JSON || true
{
  "dashboard": $(cat "$HEALTH_JSON_PATH"),
  "overwrite": true,
  "inputs": [
    {"name": "__DS_PROM__", "type": "datasource", "pluginId": "prometheus", "value": "host-prom"}
  ],
  "folderId": 0
}
JSON

echo "Provisioning complete. Open $GRAFANA_URL and search for 'PMOVES Overview' and 'PMOVES Services Health'."
