# [DEPRECATED] PMOVES MCP PRO+ Upgrades

This add-on pack is superseded by `core/` + `features/` overlays with the PMOVES‑BotZ gateway. See `docs/SETUP_GUIDE.md` for current commands.

This add-on pack previously included:
1) **Local Postman MCP (STDIO)** overlay for offline/local use.
2) **Docling VLM overlay** to run the VL pipeline (`--pipeline vlm`).
3) **Automated Postman collection generator** from OpenAPI.
4) **Nightly regression CI** via GitHub Actions + Slack notify.
5) **Kilo configs** to launch Postman as a process and a WM+VL guard mode.

## Overlays
- Local Postman:
  ```bash
  docker compose -f docker-compose.mcp-pro.yml -f docker-compose.mcp-pro.local-postman.yml up -d postman-mcp-local
  # Then, in Kilo, use kilocode/mcp_local_postman.json to connect using a process config.
  ```
- Docling VLM:
  ```bash
  docker compose -f docker-compose.mcp-pro.yml -f docker-compose.mcp-pro.vlm.yml up -d docling-mcp
  ```

## Auto collection from OpenAPI
```bash
pip install -r tools/requirements.txt
export POSTMAN_API_KEY=pmak-...
# optional: export POSTMAN_WORKSPACE_ID=...
python tools/auto_collection_from_openapi.py specs/openapi.json "PMOVES Auto"
# -> uploads to Postman; without POSTMAN_API_KEY writes out.collection.json
```

## Nightly regression (GitHub Actions)
- Add repository secrets: `POSTMAN_API_KEY`, `POSTMAN_WORKSPACE_ID` (optional), `SLACK_WEBHOOK_URL`
- Place your spec in `specs/openapi.json` or `specs/openapi.yaml`
- Workflow file: `.github/workflows/nightly_regression.yml`

## Kilo
- Use `kilocode/mcp_local_postman.json` if you want to run Postman MCP as a **process**.
- Extra mode: `pmoves-wm-vl-guard` for orchestrated flows with VL QA.

> Notes:
> - The collection generator is intentionally minimal (method + path). Extend it to include headers/body/auth based on your spec or Docling output.
> - For richer automation entirely via MCP, wire Docling’s extracted catalog into Postman tools through Kilo plans or n8n.
