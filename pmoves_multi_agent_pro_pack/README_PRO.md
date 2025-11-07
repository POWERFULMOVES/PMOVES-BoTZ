# PMOVES MCP PRO Pack (Docling + Postman + E2B + VL Sentinel + Kilo)

This pack extends the multi-agent setup with **E2B sandboxes** for safe code execution and a **Vision‑Language sentinel** for monitoring/guidance. 

## Services
- **docling-mcp** — HTTP MCP server for document parsing (http://127.0.0.1:3020) — start via `docling-mcp-server --transport streamable-http`. 
- **e2b-runner** — FastAPI shim over E2B Python SDK (`/sandbox/run|exec|stop`). Requires `E2B_API_KEY`.
- **vl-sentinel** — Vision guidance (`/vl/guide`) via **Ollama** (default) or **OpenAI**.
- **mcp-gateway** — Aggregates Docling + Postman (remote HTTP full at `https://mcp.postman.com/mcp` with `Authorization: Bearer ${POSTMAN_API_KEY}`).

## Quick Start
```bash
export TS_AUTHKEY='tskey-ephemeral-...'
export POSTMAN_API_KEY='pmak-...'
export E2B_API_KEY='e2b_...'   # from https://e2b.dev/docs
# (optional) for local vision: ollama pull qwen2.5-vl:14b && export OLLAMA_BASE_URL=http://localhost:11434

docker compose -f docker-compose.mcp-pro.yml up -d --build

# Endpoints
#  Gateway: http://127.0.0.1:2091 (served over Tailscale HTTPS)
#  Docling MCP: http://127.0.0.1:3020
#  E2B Runner:  http://127.0.0.1:7071
#  VL Sentinel: http://127.0.0.1:7072
```

## Kilo Code
- Add `kilocode/mcp.json` to Kilo MCP settings (Docling HTTP + Postman remote HTTP). 
- Import modes from `kilocode/modes/` (docling/postman/code-runner/auto-research).
- Use orchestrator to route tasks: **Docling → Postman → E2B → VL**.

## ChatGPT Desktop
- Add the **MCP Gateway** URL (`https://<tailnet-host>.ts.net/mcp`).
- Add **Actions** using `actions_e2b.yaml` and `actions_vl_sentinel.yaml` if you want direct access to E2B and VL in the same GPT.

## Notes
- Postman remote server endpoints for **Full** mode are `https://mcp.postman.com/mcp` (US) and `https://mcp.eu.postman.com/mcp` (EU). Use the `Authorization: Bearer <POSTMAN_API_KEY>` header.
- Docling MCP can be launched with `uvx --from docling-mcp docling-mcp-server --transport streamable-http` in non-Docker hosts.
- E2B SDK reference shows `from e2b_code_interpreter import Sandbox; sandbox = Sandbox.create(); sandbox.run_code(...)`.

See `workflows/n8n/docling_postman_vl.json` for an illustrative HTTP-chain flow.