# [DEPRECATED] PMOVES Multi-Agent MCP Pack (Docling + Postman + Kilo)

This pack is superseded by the unified overlays under `core/` + `features/` and the PMOVES‑BotZ gateway. Use:

```
docker compose --env-file .env \
  -f core/docker-compose/base.yml \
  -f features/pro/docker-compose.yml \
  up -d
```

For details, see `docs/SETUP_GUIDE.md`.

This pack adds **Docling MCP** (Docker HTTP server) and **Postman MCP** (hosted HTTP) to your portable agent box, plus **Kilo Code** modes and templates.

## Run
```bash
export TS_AUTHKEY='tskey-ephemeral-...'
docker compose -f docker-compose.pmoves-multi.yml up -d --build
# Docling MCP: http://127.0.0.1:3020
# Gateway (tailscale served): http://127.0.0.1:2091  => https://<your-node>.ts.net/mcp
```

### Postman MCP (HTTP)
Use the hosted server with an Authorization header:
- URL (full mode): `https://mcp.postman.com/mcp`
- Header: `Authorization: Bearer ${POSTMAN_API_KEY}`

> You can also run Postman’s **local STDIO** server with Node/Docker if your host supports STDIO integrations (see their README/DOCKER.md).

## Kilo Code
- Copy `kilocode/mcp.json` into your Kilo configuration, and add your `${POSTMAN_API_KEY}`.
- Import the custom modes from `kilocode/modes/`.
- Start in **Orchestrator** and let it route tasks between Docling and Postman.

## Notes
- Docling server runs with `--transport streamable-http` so other clients can connect.
- All config is **env-first**. Put keys in `.env` or export as runtime envs.
