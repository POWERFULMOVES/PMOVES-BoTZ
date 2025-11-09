# PMOVES MCP PRO Pack (Docling + Postman + E2B + VL Sentinel + Kilo)

This pack extends the multi-agent setup with **E2B sandboxes** for safe code execution and a **Vision‑Language sentinel** for monitoring/guidance.

## ⚠️ Current Status - Known Issues

**CRITICAL**: The docling-mcp service currently has implementation bugs that prevent proper startup and HTTP transport functionality. See [REMEDIATION_PLAN.md](../REMEDIATION_PLAN.md) for detailed issue analysis and resolution steps.

### Known Issues:
1. **Docling-MCP Server**: Implementation bugs prevent proper HTTP transport startup
2. **MCP Gateway Integration**: Connection failures due to incorrect server initialization
3. **Docker Health Checks**: Services failing health checks due to improper startup sequence
4. **SSE Transport**: Server-Sent Events not properly implemented

### Temporary Workarounds:
- Use stdio transport instead of HTTP transport for docling-mcp
- Manually start services in specific order if HTTP transport is required
- Check service logs for specific error messages during startup

## Services
- **docling-mcp** — HTTP MCP server for document parsing (http://127.0.0.1:3020) — currently has startup issues
- **e2b-runner** — FastAPI shim over E2B Python SDK (`/sandbox/run|exec|stop`). Requires `E2B_API_KEY`.
- **vl-sentinel** — Vision guidance (`/vl/guide`) via **Ollama** (default) or **OpenAI**.
- **mcp-gateway** — Aggregates Docling + Postman (remote HTTP full at `https://mcp.postman.com/mcp` with `Authorization: Bearer ${POSTMAN_API_KEY}`).

## Quick Start
```bash
export TS_AUTHKEY='tskey-ephemeral-...'
export POSTMAN_API_KEY='pmak-...'
export E2B_API_KEY='e2b_...'   # from https://e2b.dev/docs
# (optional) for local vision: ollama pull qwen2.5-vl:14b && export OLLAMA_BASE_URL=http://localhost:11434

# Build and start services (docling-mcp may fail initially)
docker compose -f docker-compose.mcp-pro.yml up -d --build

# Endpoints
#  Gateway: http://127.0.0.1:2091 (served over Tailscale HTTPS)
#  Docling MCP: http://127.0.0.1:3020 (may be unavailable due to bugs)
#  E2B Runner:  http://127.0.0.1:7071
#  VL Sentinel: http://127.0.0.1:7072
```

## Troubleshooting

### Docling-MCP Service Issues
If docling-mcp fails to start:
```bash
# Check logs for specific errors
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1

# Try manual startup
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python docling_mcp_server.py --transport stdio

# Test HTTP endpoint manually
curl -H "Accept: text/event-stream" http://localhost:3020/mcp
```

### Service Dependency Issues
If services fail to start in correct order:
```bash
# Start services individually
docker compose -f docker-compose.mcp-pro.yml up -d docling-mcp
sleep 30
docker compose -f docker-compose.mcp-pro.yml up -d mcp-gateway
docker compose -f docker-compose.mcp-pro.yml up -d e2b-runner vl-sentinel
```

## Kilo Code
- Add `kilocode/mcp.json` to Kilo MCP settings (Docling HTTP + Postman remote HTTP).
- Import modes from `kilocode/modes/` (docling/postman/code-runner/auto-research).
- Use orchestrator to route tasks: **Docling → Postman → E2B → VL**.

**Note**: Due to current docling-mcp issues, you may need to use alternative document processing methods or wait for the remediation to be completed.

## ChatGPT Desktop
- Add the **MCP Gateway** URL (`https://<tailnet-host>.ts.net/mcp`).
- Add **Actions** using `actions_e2b.yaml` and `actions_vl_sentinel.yaml` if you want direct access to E2B and VL in the same GPT.

## Notes
- Postman remote server endpoints for **Full** mode are `https://mcp.postman.com/mcp` (US) and `https://mcp.eu.postman.com/mcp` (EU). Use the `Authorization: Bearer <POSTMAN_API_KEY>` header.
- Docling MCP can be launched with `uvx --from docling-mcp docling-mcp-server --transport streamable-http` in non-Docker hosts (currently unreliable).
- E2B SDK reference shows `from e2b_code_interpreter import Sandbox; sandbox = Sandbox.create(); sandbox.run_code(...)`.

See `workflows/n8n/docling_postman_vl.json` for an illustrative HTTP-chain flow.

## Development Status
- **Last Updated**: November 2025
- **Known Issues**: See REMEDIATION_PLAN.md for comprehensive issue analysis
- **Next Steps**: Implementation of fixes is in progress