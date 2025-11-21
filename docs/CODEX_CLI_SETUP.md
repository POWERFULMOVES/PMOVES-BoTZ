# Codex CLI / Kilo MCP Setup

## Use PMOVES‑BotZ Gateway (recommended)
- The gateway aggregates MCP servers (Docling, Cipher, Postman, etc.).
- Local host:
```
config/codex/mcp_gateway.json  # use pmoves-gateway-local (http://localhost:2091)
```
- pmoves-net (inside Docker network):
```
config/codex/mcp_gateway.json  # use pmoves-gateway-net (http://mcp-gateway:8000)
```

## Direct cipher (optional)
- For tools that require direct HTTP connection to Cipher:
```
config/codex/mcp_gateway.json  # cipher-direct (http://localhost:3011)
```

## Kilo example
- In Kilo settings, add an MCP server from the JSON above (transport: http, URL per your environment). Prefer the gateway.

## Notes
- The gateway catalog (core/mcp_catalog.yaml) includes docling + cipher; extend as needed.
- For pmoves-net use service DNS names:
  - Gateway: http://mcp-gateway:8000
  - Cipher:  http://cipher-memory:3011

