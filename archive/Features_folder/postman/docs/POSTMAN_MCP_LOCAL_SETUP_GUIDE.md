# Postman MCP Local Service Setup Guide

## Overview

The Postman MCP Local service is a **stdio-based MCP server** that provides 108 tools for interacting with Postman's API. This service loads successfully but exits immediately when run in Docker without a connected client because it's designed to communicate via stdio with an MCP client.

## Key Understanding

**Important**: The Postman MCP Local service is working correctly when it:
1. Loads 108 tools successfully
2. Shows "Server connected and ready" message
3. Exits with code 0

This is **expected behavior** for a stdio-based MCP server that doesn't have a connected client.

## Configuration Files

### 1. Environment Configuration (.env)
```bash
# PMOVES Pro Plus Pack Environment Variables
# Postman MCP Local configuration
POSTMAN_API_KEY=PMAK-690e5c6600414a0001f14674-3167c3686c5e852470b7a045287475b307
POSTMAN_API_BASE_URL=https://api.postman.com
```

### 2. Docker Compose Configuration
The [`docker-compose.mcp-pro.local-postman.yml`](docker-compose.mcp-pro.local-postman.yml) file defines the service:

```yaml
services:
  postman-mcp-local:
    image: node:20-alpine
    working_dir: /srv
    environment:
      POSTMAN_API_KEY: PMAK-690e5c6600414a0001f14674-3167c3686c5e852470b7a045287475b307
      POSTMAN_API_BASE_URL: https://api.postman.com
    entrypoint: ["sh","-lc"]
    command: >
      "npx @postman/postman-mcp-server@latest --full"
    network_mode: host
    restart: unless-stopped
```

### 3. Kilo Code Configuration
The [`kilocode/mcp_local_postman.json`](kilocode/mcp_local_postman.json) file defines how to connect to this service:

```json
{
  "mcpServers": {
    "postman-local": {
      "command": "npx",
      "args": ["@postman/postman-mcp-server@latest", "--full"],
      "env": {
        "POSTMAN_API_KEY": "PMAK-690e5c6600414a0001f14674-3167c3686c5e852470b7a045287475b307",
        "POSTMAN_API_BASE_URL": "https://api.postman.com"
      }
    }
  }
}
```

## How to Use Postman MCP Local Service

### Method 1: Direct Script Execution (Recommended)

#### For Linux/macOS:
```bash
# Make script executable
chmod +x run_postman_mcp_local.sh

# Set environment variables
export POSTMAN_API_KEY=PMAK-690e5c6600414a0001f14674-3167c3686c5e852470b7a045287475b307
export POSTMAN_API_BASE_URL=https://api.postman.com

# Run the service
./run_postman_mcp_local.sh
```

#### For Windows:
```powershell
# Set environment variables
$env:POSTMAN_API_KEY = "PMAK-690e5c6600414a0001f14674-3167c3686c5e852470b7a045287475b307"
$env:POSTMAN_API_BASE_URL = "https://api.postman.com"

# Run the service
.\run_postman_mcp_local.ps1
```

### Method 2: Docker Compose (For Testing)

```bash
# Start the service (will exit immediately - this is expected)
docker-compose -f docker-compose.mcp-pro.local-postman.yml up postman-mcp-local

# View logs to confirm it's working
docker-compose -f docker-compose.mcp-pro.local-postman.yml logs postman-mcp-local
```

### Method 3: Kilo Code Integration

The Postman MCP Local service is designed to be used with Kilo Code as a process-based MCP server. The configuration in [`kilocode/mcp_local_postman.json`](kilocode/mcp_local_postman.json) tells Kilo Code how to start and connect to this service.

## Expected Behavior

When you run the Postman MCP Local service, you should see:

1. **Tool Loading**: 108 tools loaded
2. **Server Initialization**: Server starting up
3. **Ready State**: "Server connected and ready: @postman/postman-mcp-server@2.4.2 with 108 tools (full)"
4. **Exit**: Service exits with code 0 (when no client is connected)

This is **normal and expected** behavior for a stdio-based MCP server.

## Troubleshooting

### Issue: Service exits immediately
**Solution**: This is expected behavior. The service needs an MCP client to connect to it via stdio.

### Issue: "POSTMAN_API_KEY environment variable is required"
**Solution**: Ensure the POSTMAN_API_KEY environment variable is set before starting the service.

### Issue: Permission denied on script
**Solution**: Make the script executable:
```bash
chmod +x run_postman_mcp_local.sh
```

## Available Tools

The Postman MCP Local service provides 108 tools including:
- Collection management (create, read, update, delete)
- Environment management
- Mock server management
- Monitor management
- API specification management
- Workspace management
- And many more...

## Integration with Other Services

The Postman MCP Local service can be integrated with:
- **Kilo Code**: As a process-based MCP server
- **MCP Gateway**: For HTTP-based access to stdio services
- **Custom MCP clients**: Any client that supports stdio transport

## Summary

The Postman MCP Local service is now properly configured and ready to use. The key points to remember:

1. It's a **stdio-based** MCP server, not an HTTP service
2. It **exits immediately** when not connected to a client (this is normal)
3. Use the provided scripts for easy startup
4. Configure environment variables before starting
5. Use with Kilo Code or other MCP clients for full functionality

The service is working correctly - it just needs to be connected to an MCP client to be useful.