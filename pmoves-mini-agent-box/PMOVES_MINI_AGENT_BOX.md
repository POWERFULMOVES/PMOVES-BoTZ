# pmoves-mini Agent Box (Portable) — MCP + Tailscale

Spin up a self-contained MCP Gateway that can reach your pmoves services and be accessed online via Tailscale (Serve/Funnel).

## What’s inside
- **tailscale**: exposes the MCP port as HTTPS on your Tailscale name; optional Funnel for public internet.
- **mcp-gateway**: runs Docker MCP Gateway with a **portable** catalog (Docling 1.3.1 via pipx).
- Reads `env.shared`, `.env`, `.env.local` for config.

## Start
### Linux/WSL
```bash
export TS_AUTHKEY='tskey-ephemeral-...'
./run_pmoves_mini.sh
```
### Windows PowerShell
```powershell
.un_pmoves_mini.ps1 -TS_AUTHKEY "tskey-ephemeral-..."
```

## Connect from ChatGPT Desktop
Use your **Tailscale HTTPS** URL and append `/mcp`:
```
https://<your-tailscale-name>.ts.net/mcp
```

## Project network (optional)
Switch from host networking to your project network to use in-cluster DNS like `meilisearch:7700`.