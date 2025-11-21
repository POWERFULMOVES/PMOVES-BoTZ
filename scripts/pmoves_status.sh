#!/usr/bin/env bash
set -euo pipefail

ns=${PMZ_NAMESPACE:-${COMPOSE_PROJECT_NAME:-pmoves-botz}}
mode="normal"
[[ "${PMZ_INTERNAL_ONLY:-}" == "1" ]] && mode="internal-only"
[[ "${PMZ_EPHEMERAL:-}" == "1" ]] && mode="ephemeral"

echo "PMOVES-BotZ Status"
echo "- Namespace: $ns"
echo "- Port mode: $mode"
echo "- pmoves-net: ${PMOVES_AI_NETWORK:-pmoves-net}"

host_port(){
  local svc=$1 cport=$2
  local name="${ns}-${svc}-1"
  docker inspect -f '{{ (index (index .NetworkSettings.Ports "'"${cport}/tcp"'") 0).HostPort }}' "$name" 2>/dev/null || true
}

print_row(){ printf "%-16s %-36s\n" "$1" "$2"; }

echo "\nEndpoints (host):"
print_row Gateway "http://localhost:${GATEWAY_PORT:-$(host_port mcp-gateway 8000)}/ready"
print_row Docling "http://localhost:${DOCLING_PORT:-$(host_port docling-mcp 3020)}/health"
print_row Cipher  "http://localhost:${CIPHER_API_PORT:-$(host_port cipher-memory 3011)}/health"

echo "\nEndpoints (pmoves-net DNS):"
print_row Gateway "http://mcp-gateway:8000"
print_row Docling "http://docling-mcp:3020"
print_row Cipher  "http://cipher-memory:3011"
print_row E2B     "http://e2b-runner:7071"
print_row VL      "http://vl-sentinel:7072"

echo "\nAutodiscovered blackbox targets:"
if [[ -f features/metrics/file_sd/blackbox_targets.yml ]]; then
  cat features/metrics/file_sd/blackbox_targets.yml
else
  echo "(none yet)"
fi

