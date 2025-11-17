#!/bin/bash

# Postman MCP Local Service Runner
# This script runs the Postman MCP Local service as a stdio-based MCP server
# 
# Usage: ./run_postman_mcp_local.sh
# 
# The service will start and wait for MCP client connections via stdio
# This is the correct way to run stdio-based MCP servers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Postman MCP Local Service Runner${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if POSTMAN_API_KEY is set
if [ -z "$POSTMAN_API_KEY" ]; then
    echo -e "${RED}Error: POSTMAN_API_KEY environment variable is not set${NC}"
    echo -e "${YELLOW}Please set the POSTMAN_API_KEY environment variable:${NC}"
    echo -e "${YELLOW}export POSTMAN_API_KEY=your_api_key_here${NC}"
    exit 1
fi

# Check if POSTMAN_API_BASE_URL is set
if [ -z "$POSTMAN_API_BASE_URL" ]; then
    echo -e "${YELLOW}Warning: POSTMAN_API_BASE_URL not set, using default${NC}"
    export POSTMAN_API_BASE_URL="https://api.postman.com"
fi

echo -e "${GREEN}Configuration:${NC}"
echo -e "  POSTMAN_API_KEY: ${POSTMAN_API_KEY:0:10}..."
echo -e "  POSTMAN_API_BASE_URL: $POSTMAN_API_BASE_URL"

echo -e "\n${GREEN}Starting Postman MCP Local service...${NC}"
echo -e "${YELLOW}Note: This is a stdio-based MCP server that waits for client connections${NC}"
echo -e "${YELLOW}The service will appear to hang - this is normal behavior${NC}"
echo -e "${YELLOW}Use Ctrl+C to stop the service${NC}\n"

# Run the Postman MCP server
# Using npx to ensure we have the latest version
npx @postman/postman-mcp-server@latest --full

echo -e "\n${BLUE}Postman MCP Local service stopped${NC}"