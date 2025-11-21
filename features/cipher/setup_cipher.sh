#!/bin/bash
# Setup script for Pmoves-cipher integration

set -e

echo "Setting up Pmoves-cipher integration..."

# Check if Node.js and pnpm are installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js first."
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm globally..."
    npm install -g pnpm
fi

# Navigate to cipher submodule
cd "$(dirname "$0")/pmoves_cipher"

echo "Installing cipher dependencies..."
pnpm install --frozen-lockfile

echo "Building cipher..."
pnpm run build:no-ui

echo "Creating cipher configuration..."
# Create a PMOVES-specific configuration
cat > memAgent/cipher_pmoves.yml << 'EOF'
# PMOVES-specific Cipher Configuration
mcpServers: {}

llm:
  provider: openai
  model: gpt-4.1-mini
  apiKey: $OPENAI_API_KEY
  maxIterations: 50

embedding:
  type: openai
  model: text-embedding-3-small
  apiKey: $OPENAI_API_KEY

systemPrompt:
  enabled: true
  content: |
    You are an AI memory assistant for PMOVES (Portable Multi-Agent Orchestration and Validation Environment System).
    You excel at:
    - Storing and retrieving coding knowledge
    - Managing multi-agent workflow context
    - Preserving reasoning patterns across sessions
    - Maintaining project-specific memory
    
    You should organize memories by agent type, project context, and workflow stage.
EOF

echo "Cipher setup completed successfully!"
echo "Configuration saved to: memAgent/cipher_pmoves.yml"
echo ""
echo "To use cipher memory, set the following environment variables:"
echo "- OPENAI_API_KEY (required)"
echo "- CIPHER_CONFIG_PATH=memAgent/cipher_pmoves.yml (optional)"
echo ""
echo "Then run: python3 app_cipher_memory.py"