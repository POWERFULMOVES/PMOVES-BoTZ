#!/usr/bin/env bash
set -euo pipefail
: "${TS_AUTHKEY:?Set TS_AUTHKEY (ephemeral) before running}"
docker compose -f ./docker-compose.pmoves-multi.yml up -d --build
echo "Docling MCP:  http://127.0.0.1:3020"
echo "Gateway:      http://127.0.0.1:2091  (Tailscale Serve exposes HTTPS on your tailnet)"