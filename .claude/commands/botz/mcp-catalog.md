# BoTZ MCP Catalog

View the MCP server catalog and available tools.

## Arguments

- `$ARGUMENTS` - Optional: specific server name to get details (docling, e2b, cipher-memory, vl-sentinel, postman, n8n-agent, hostinger)

## Instructions

1. Read the MCP catalog from `core/mcp/catalog.yml`
2. If specific server requested, show detailed config
3. List available tools for each server

```bash
# View full catalog
cat /home/pmoves/PMOVES.AI/PMOVES-BoTZ/core/mcp/catalog.yml

# If checking specific server, also try to list its tools
# Example for Docling:
curl -s http://localhost:3020/tools 2>/dev/null | jq '.' || echo "Server not responding"
```

## MCP Servers Reference

| Server | Port/Transport | Purpose |
|--------|---------------|---------|
| docling | SSE :3020 | Document conversion |
| e2b | SSE :7071 | Code sandbox |
| vl-sentinel | SSE :7072 | Vision-language |
| cipher-memory | stdio | Persistent memory |
| postman | stdio | API testing |
| n8n-agent | stdio | Workflow automation |
| hostinger | stdio | VPS management |

Report:
- Server configurations
- Transport types (SSE vs stdio)
- Required environment variables
- Available tools (if server is running)
