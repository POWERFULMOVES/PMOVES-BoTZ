#!/usr/bin/env bash
set -euo pipefail

# Defaults (override via env)
PMZ_NAMESPACE=${PMZ_NAMESPACE:-botz-dev}
export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME:-$PMZ_NAMESPACE}
export PMOVES_AI_NETWORK=${PMOVES_AI_NETWORK:-pmoves-net}

# Local-first bootstrap: ensure a root .env exists so users stay at repo root
if [[ ! -f .env ]]; then
  echo "[0/4] No .env found — bootstrapping from examples (local-first, Ollama)…"
  if [[ -f ./scripts/setup_pmoves.sh ]]; then
    ./scripts/setup_pmoves.sh -c pro || true
  elif [[ -f ./core/example.env ]]; then
    cp ./core/example.env ./.env || true
  fi
fi

export GATEWAY_PORT=${GATEWAY_PORT:-2091}
export DOCLING_PORT=${DOCLING_PORT:-3020}
export E2B_PORT=${E2B_PORT:-7071}
export VL_PORT=${VL_PORT:-7072}
export CRUSH_PORT=${CRUSH_PORT:-7069}
export PROMETHEUS_PORT=${PROMETHEUS_PORT:-9090}
export GRAFANA_PORT=${GRAFANA_PORT:-3033}
export ALERTMANAGER_PORT=${ALERTMANAGER_PORT:-9093}
export CIPHER_UI_PORT=${CIPHER_UI_PORT:-3010}
export CIPHER_API_PORT=${CIPHER_API_PORT:-3011}

# Local-first defaults: prefer Ollama
export VL_PROVIDER=${VL_PROVIDER:-ollama}
export OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
echo "Local-first mode: VL_PROVIDER=${VL_PROVIDER} OLLAMA_BASE_URL=${OLLAMA_BASE_URL}"

echo "[1/4] Rebuilding Docling MCP (no cache) ..."
docker compose --env-file .env -f core/docker-compose/base.yml build --no-cache docling-mcp

echo "[2/4] Starting PMOVES-BotZ core + pro + metrics on '$PMZ_NAMESPACE' (network: $PMOVES_AI_NETWORK) ..."

COMPOSE_ARGS=(
  -f core/docker-compose/base.yml
  -f features/pro/docker-compose.yml
  -f features/network/external.yml
  -f features/metrics/docker-compose.yml
  -f features/cipher/docker-compose.yml
)

# Optional internal-only (no host ports) or ephemeral host ports
if [[ "${PMZ_INTERNAL_ONLY:-}" == "1" ]]; then
  COMPOSE_ARGS+=( -f features/network/internal.yml )
elif [[ "${PMZ_EPHEMERAL:-}" == "1" ]]; then
  COMPOSE_ARGS+=( -f features/network/ephemeral.yml )
fi

docker compose --env-file .env "${COMPOSE_ARGS[@]}" up -d

echo "[3/4] Checking health ..."
sleep 5
set +e
curl -fsS http://localhost:${GATEWAY_PORT}/ready >/dev/null && echo "Gateway OK" || echo "Gateway not ready"
curl -fsS http://localhost:${DOCLING_PORT}/health >/dev/null && echo "Docling OK" || echo "Docling not ready"
set -e

echo "[4/4] Autodiscover Prometheus targets and reload ..."
python3 ./scripts/prom_autodiscover.py || true

echo "Provision existing Grafana (3002) if reachable ..."
if curl -fsS http://localhost:3002/login >/dev/null 2>&1; then
  ./scripts/grafana_provision.sh
else
  echo "grafana-1 (3002) not reachable; skipping external provisioning"
fi

echo "Done. Prometheus: http://localhost:${PROMETHEUS_PORT} Grafana: http://localhost:${GRAFANA_PORT}"
