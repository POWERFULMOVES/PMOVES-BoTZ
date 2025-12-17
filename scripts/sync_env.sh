#!/usr/bin/env bash
# Sync required API keys from parent pmoves/env.shared to PMOVES-BoTZ .env
#
# Usage: ./scripts/sync_env.sh
#
# This script extracts required API keys from the parent PMOVES.AI repository
# and merges them into the local .env file for PMOVES-BoTZ services.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOTZ_ROOT="$(dirname "$SCRIPT_DIR")"
PARENT_ENV="${BOTZ_ROOT}/../pmoves/env.shared"
ROOT_ENV="${BOTZ_ROOT}/.env"
EXAMPLE_ENV="${BOTZ_ROOT}/core/example.env"

# Required keys for e2e tests and service operation
REQUIRED_KEYS=(
    # LLM Providers
    "VENICE_API_KEY"
    "OPENAI_API_KEY"
    "ANTHROPIC_API_KEY"
    "GROQ_API_KEY"
    "GEMINI_API_KEY"

    # TensorZero Gateway
    "TENSORZERO_URL"
    "TENSORZERO_BASE_URL"
    "TENSORZERO_CHAT_MODEL"
    "TENSORZERO_EMBED_MODEL"

    # Service-specific
    "N8N_API_KEY"
    "E2B_API_KEY"
    "HOSTINGER_API_KEY"

    # Infrastructure
    "TAILSCALE_AUTHKEY"
    "OLLAMA_BASE_URL"

    # Cipher
    "CIPHER_ENCRYPTION_KEY"
)

echo "Syncing environment from parent repository..."

# Create .env from example if it doesn't exist
if [[ ! -f "$ROOT_ENV" ]]; then
    if [[ -f "$EXAMPLE_ENV" ]]; then
        cp "$EXAMPLE_ENV" "$ROOT_ENV"
        echo "  Created .env from example.env"
    else
        touch "$ROOT_ENV"
        echo "  Created empty .env"
    fi
fi

# Check if parent env exists
if [[ ! -f "$PARENT_ENV" ]]; then
    echo "Warning: Parent env.shared not found at $PARENT_ENV"
    echo "  Using local .env values only"
    echo "  To sync keys, ensure PMOVES.AI/pmoves/env.shared exists"
    exit 0
fi

synced_count=0
skipped_count=0

# Extract and merge keys from parent
for key in "${REQUIRED_KEYS[@]}"; do
    # Get value from parent (handle various formats)
    value=$(grep -E "^${key}=" "$PARENT_ENV" 2>/dev/null | head -1 | cut -d'=' -f2- || true)

    # Skip empty, placeholder, or test values
    if [[ -z "$value" || "$value" == '""' || "$value" == "''" || "$value" == "CHANGE_ME"* || "$value" == "test_"* || "$value" == "your_"* ]]; then
        skipped_count=$((skipped_count + 1))
        continue
    fi

    # Update or append to root .env
    if grep -q "^${key}=" "$ROOT_ENV" 2>/dev/null; then
        # Check if current value is a placeholder
        current=$(grep -E "^${key}=" "$ROOT_ENV" | head -1 | cut -d'=' -f2-)
        if [[ "$current" == "CHANGE_ME"* || "$current" == "test_"* || "$current" == "your_"* || -z "$current" ]]; then
            # Replace placeholder with real value
            sed -i "s|^${key}=.*|${key}=${value}|" "$ROOT_ENV"
            echo "  Updated $key"
            synced_count=$((synced_count + 1))
        fi
    else
        # Append new key
        echo "${key}=${value}" >> "$ROOT_ENV"
        echo "  Added $key"
        synced_count=$((synced_count + 1))
    fi
done

echo ""
echo "Environment sync complete:"
echo "  Synced: $synced_count keys"
echo "  Skipped: $skipped_count keys (empty or placeholder in parent)"
echo ""
echo "Run 'make env-verify' to validate configuration"
