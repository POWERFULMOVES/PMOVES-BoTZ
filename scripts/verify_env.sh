#!/bin/bash

# PMOVES MCP Environment Verification Script
# This script verifies that all required environment variables are properly configured

echo "=== PMOVES MCP Environment Variable Verification ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if variable exists and is not empty
check_var() {
    local var_name=$1
    local var_value=${!var_name}
    
    if [ -z "$var_value" ]; then
        echo -e "${RED}❌ $var_name is not set or empty${NC}"
        return 1
    else
        echo -e "${GREEN}✅ $var_name is set${NC}"
        return 0
    fi
}

# Function to check if variable exists in docker-compose
check_docker_compose_var() {
    local var_name=$1
    local file="docker-compose.mcp-pro.yml"
    
    if grep -q "\${$var_name}" "$file"; then
        echo -e "${GREEN}✅ $var_name is referenced in docker-compose.mcp-pro.yml${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  $var_name is not referenced in docker-compose.mcp-pro.yml${NC}"
        return 1
    fi
}

echo "Checking required environment variables..."
echo ""

# Required variables for MCP services
required_vars=(
    "OPENAI_API_KEY"
    "VENICE_API_KEY"
    "TAILSCALE_AUTHKEY"
    "E2B_API_KEY"
    "PMOVES_ROOT"
)

# Load environment from files
if [ -f ".env" ]; then
    echo "Loading environment from .env..."
    set -a
    source .env
    set +a
fi

if [ -f ".env.local" ]; then
    echo "Loading environment from .env.local..."
    set -a
    source .env.local
    set +a
fi

if [ -f "env.shared" ]; then
    echo "Loading environment from env.shared..."
    set -a
    source env.shared
    set +a
fi

echo ""

# Check each required variable
all_vars_set=true
for var in "${required_vars[@]}"; do
    if ! check_var "$var"; then
        all_vars_set=false
    fi
done

echo ""
echo "Checking docker-compose configuration..."
echo ""

# Check if variables are properly referenced in docker-compose
for var in "${required_vars[@]}"; do
    check_docker_compose_var "$var"
done

echo ""
echo "=== Verification Summary ==="
echo ""

if [ "$all_vars_set" = true ]; then
    echo -e "${GREEN}✅ All required environment variables are set!${NC}"
else
    echo -e "${RED}❌ Some environment variables are missing. Please check the configuration.${NC}"
fi

echo ""
echo "=== Next Steps ==="
echo ""
echo "1. If any variables are missing, add them to the appropriate .env file"
echo "2. Restart the MCP services with:"
echo "   docker-compose -f docker-compose.mcp-pro.yml down"
echo "   docker-compose -f docker-compose.mcp-pro.yml up -d"
echo ""
echo "3. Check service logs to verify everything is working:"
echo "   docker-compose -f docker-compose.mcp-pro.yml logs tailscale"
echo "   docker-compose -f docker-compose.mcp-pro.yml logs mcp-gateway"
echo "   docker-compose -f docker-compose.mcp-pro.yml logs cipher-memory"
echo ""