#!/bin/sh
# Hostinger MCP Server Entrypoint
# Runs the official hostinger-api-mcp package

if [ -z "$API_TOKEN" ] && [ -z "$HOSTINGER_API_KEY" ]; then
    echo "ERROR: API_TOKEN or HOSTINGER_API_KEY environment variable required"
    exit 1
fi

# Use API_TOKEN if set, otherwise fall back to HOSTINGER_API_KEY
export API_TOKEN="${API_TOKEN:-$HOSTINGER_API_KEY}"

# Run hostinger-api-mcp via npx (uses globally installed version)
exec hostinger-api-mcp
