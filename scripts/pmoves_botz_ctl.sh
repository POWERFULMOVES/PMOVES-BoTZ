#!/usr/bin/env bash
set -euo pipefail

CMD=${1:-help}
shift || true

BASE="-f core/docker-compose/base.yml -f features/pro/docker-compose.yml -f features/network/external.yml -f features/metrics/docker-compose.yml -f features/cipher/docker-compose.yml"

case "$CMD" in
  up)
    docker compose --env-file .env $BASE up -d ;;
  down)
    docker compose --env-file .env $BASE down ;;
  rebuild)
    docker compose --env-file .env -f core/docker-compose/base.yml build --no-cache docling-mcp ;;
  logs)
    docker compose $BASE logs -f ${1:-} ;;
  health)
    set +e
    echo "Gateway:"; curl -fsS http://localhost:${GATEWAY_PORT:-2091}/ready || echo fail
    echo "Docling:"; curl -fsS http://localhost:${DOCLING_PORT:-3020}/health || echo fail
    set -e ;;
  metrics)
    echo "Prometheus targets:"; curl -fsS http://localhost:${PROMETHEUS_PORT:-9090}/targets || true ;;
  provision-grafana-existing)
    ./scripts/grafana_provision.sh ;;
  *)
    echo "Usage: $0 {up|down|rebuild|logs [svc]|health|metrics|provision-grafana-existing}" ;;
esac

