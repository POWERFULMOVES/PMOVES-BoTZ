#!/usr/bin/env bash
# PMOVES-BoTZ Environment Variable Verification Script
#
# Usage: ./scripts/verify_env.sh
#
# Verifies all required environment variables are properly configured
# before starting services or running e2e tests.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOTZ_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== PMOVES-BoTZ Environment Verification ==="
echo ""

# Load environment from .env
if [[ -f "${BOTZ_ROOT}/.env" ]]; then
    echo "Loading .env..."
    set -a
    # shellcheck source=/dev/null
    source "${BOTZ_ROOT}/.env"
    set +a
else
    echo "Warning: .env not found at ${BOTZ_ROOT}/.env"
    echo "Run 'make env-init' to create it."
fi

echo ""

# Required variables
declare -A REQUIRED_VARS=(
    ["CIPHER_ENCRYPTION_KEY"]="64 hex chars for cipher encryption"
)

# LLM provider keys - at least one should be set
LLM_KEYS=("VENICE_API_KEY" "OPENAI_API_KEY" "ANTHROPIC_API_KEY" "GROQ_API_KEY")

# Optional but recommended for full functionality
declare -A OPTIONAL_VARS=(
    ["N8N_API_KEY"]="n8n workflow automation API key"
    ["TENSORZERO_URL"]="TensorZero gateway URL"
    ["OLLAMA_BASE_URL"]="Local Ollama for local-first mode"
    ["E2B_API_KEY"]="E2B sandbox API key"
    ["TAILSCALE_AUTHKEY"]="Tailscale VPN auth key"
    ["HOSTINGER_API_KEY"]="Hostinger VPS/DNS management"
)

MISSING=0
WARNINGS=0

# Check function
check_var() {
    local var_name=$1
    local value="${!var_name:-}"

    if [[ -z "$value" || "$value" == "CHANGE_ME"* || "$value" == "test_"* || "$value" == "your_"* ]]; then
        return 1
    fi
    return 0
}

# Check required vars
echo "Checking required variables..."
for var in "${!REQUIRED_VARS[@]}"; do
    desc="${REQUIRED_VARS[$var]}"
    value="${!var:-}"

    if ! check_var "$var"; then
        echo -e "  ${RED}[FAIL]${NC} $var: MISSING - $desc"
        MISSING=$((MISSING + 1))
    else
        # Validate CIPHER_ENCRYPTION_KEY length
        if [[ "$var" == "CIPHER_ENCRYPTION_KEY" && ${#value} -ne 64 ]]; then
            echo -e "  ${RED}[FAIL]${NC} $var: Invalid (must be 64 hex chars, got ${#value})"
            MISSING=$((MISSING + 1))
        else
            echo -e "  ${GREEN}[OK]${NC}   $var: configured"
        fi
    fi
done

# Check LLM provider keys (at least one required)
echo ""
echo "Checking LLM provider keys (at least one required)..."
llm_configured=0
for var in "${LLM_KEYS[@]}"; do
    if check_var "$var"; then
        echo -e "  ${GREEN}[OK]${NC}   $var: configured"
        llm_configured=$((llm_configured + 1))
    else
        echo -e "  ${YELLOW}[--]${NC}   $var: not set"
    fi
done

if [[ $llm_configured -eq 0 ]]; then
    echo -e "  ${RED}[FAIL]${NC} No LLM provider key configured!"
    echo "         Set at least one of: ${LLM_KEYS[*]}"
    MISSING=$((MISSING + 1))
fi

# Check optional vars
echo ""
echo "Checking optional variables..."
for var in "${!OPTIONAL_VARS[@]}"; do
    desc="${OPTIONAL_VARS[$var]}"

    if check_var "$var"; then
        echo -e "  ${GREEN}[OK]${NC}   $var: configured"
    else
        echo -e "  ${YELLOW}[WARN]${NC} $var: not set - $desc"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# Summary
echo ""
echo "============================================"
if [[ $MISSING -gt 0 ]]; then
    echo -e "${RED}VERIFICATION FAILED: $MISSING required variable(s) missing${NC}"
    echo ""
    echo "To fix:"
    echo "  1. Run 'make env-sync' to sync from parent repo"
    echo "  2. Or manually configure missing values in .env"
    echo ""
    echo "For CIPHER_ENCRYPTION_KEY, generate with:"
    echo "  openssl rand -hex 32"
    exit 1
fi

if [[ $WARNINGS -gt 0 ]]; then
    echo -e "${GREEN}VERIFICATION PASSED${NC} with ${YELLOW}$WARNINGS warning(s)${NC}"
    echo "Some optional features may not work without these keys."
else
    echo -e "${GREEN}VERIFICATION PASSED - All variables configured${NC}"
fi

echo ""
echo "Ready to start services with: make up"
