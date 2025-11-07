#!/usr/bin/env bash
set -euo pipefail
: "${TS_AUTHKEY:?Set TS_AUTHKEY (ephemeral) before running}"
docker compose -f ./docker-compose.pmoves-mini.yml up -d --remove-orphans
echo "==> MCP Gateway local: http://127.0.0.1:2091/mcp"
echo "==> Tailscale Serve enabled. Use 'tailscale status' for your HTTPS URL."