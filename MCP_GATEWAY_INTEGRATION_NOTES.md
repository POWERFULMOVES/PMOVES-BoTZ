# PMOVES‑BotZ Gateway Integration (Submodule)

Path: `pmoves_multi_agent_pro_pack/mcp_gateway/PMOVES-BotZ-gateway` (git submodule)
Remote: https://github.com/POWERFULMOVES/PMOVES-BotZ-gateway.git

## What Changed
- Added the forked gateway as a git submodule.
- Introduced an overlay `features/gateway-proxy/docker-compose.yml` that replaces the default Python gateway with the PMOVES‑BotZ proxy server.
- Kept external port `2091` for backward compatibility (mapped to container port `8000`).

## How To Run (overlay)
```bash
# Default (Docling proxied)
docker compose \
  -f core/docker-compose/base.yml \
  -f features/pro/docker-compose.yml \
  -f features/gateway-proxy/docker-compose.yml \
  up -d
```

Override the upstream:
```bash
export MCP_PROXY_URL=http://host:port
```

## Compatibility Notes
- Aggregation vs Proxy:
  - Existing Python gateway supported reading a catalog and listing servers.
  - PMOVES‑BotZ proxy expects either a single HTTP upstream (`MCP_PROXY_URL`) or a single STDIO command (`MCP_COMMAND` + `MCP_ARGS`).
  - Multi‑server aggregation requires extending the proxy to load a catalog file or running multiple proxy instances. For now, the overlay proxies one upstream (Docling by default).
- Health endpoint:
  - The proxy is served by `FastMCP` on port `8000`. If a `/health` route is not present, omit healthchecks or add one in the fork.
- Ports & OS support:
  - Mapped `2091:8000` to preserve docs and client settings.
  - No host networking required; works on Windows/macOS/Linux.

## Next Steps (Optional)
- Add catalog support to the fork:
  - Extend `mcp-proxy-server/src/main.py` to read `mcp_catalog.yaml` and pass the full `mcpServers` mapping to `FastMCP.as_proxy()`.
  - Or accept `MCP_CATALOG_PATH` env var pointing to YAML.
- Add `/health` route in the proxy service for clean Compose healthchecks.
- Deprecate the legacy gateway once multi‑server config parity is achieved.


