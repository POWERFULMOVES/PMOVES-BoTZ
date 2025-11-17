# Setup script for Pmoves-cipher integration (PowerShell)

Write-Host "Setting up Pmoves-cipher integration..." -ForegroundColor Green

# Check if Node.js is installed
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Node.js is not installed. Please install Node.js first." -ForegroundColor Red
    exit 1
}

# Check if pnpm is installed, install if not
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    Write-Host "Installing pnpm globally..." -ForegroundColor Yellow
    npm install -g pnpm
}

# Navigate to cipher submodule
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cipherDir = Join-Path $scriptDir "pmoves_cipher"

Set-Location $cipherDir

Write-Host "Installing cipher dependencies..." -ForegroundColor Yellow
pnpm install --frozen-lockfile

Write-Host "Building cipher..." -ForegroundColor Yellow
pnpm run build:no-ui

Write-Host "Creating cipher configuration..." -ForegroundColor Yellow

# Create a PMOVES-specific configuration
$configContent = @"
# PMOVES-specific Cipher Configuration
mcpServers: {}

llm:
  provider: openai
  model: gpt-4.1-mini
  apiKey: `$OPENAI_API_KEY
  maxIterations: 50

embedding:
  type: openai
  model: text-embedding-3-small
  apiKey: `$OPENAI_API_KEY

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
"@

$configPath = Join-Path $cipherDir "memAgent\cipher_pmoves.yml"
$configContent | Out-File -FilePath $configPath -Encoding UTF8

Write-Host "Cipher setup completed successfully!" -ForegroundColor Green
Write-Host "Configuration saved to: memAgent\cipher_pmoves.yml" -ForegroundColor Cyan
Write-Host ""
Write-Host "To use cipher memory, set the following environment variables:" -ForegroundColor Yellow
Write-Host "- OPENAI_API_KEY (required)" -ForegroundColor Cyan
Write-Host "- CIPHER_CONFIG_PATH=memAgent\cipher_pmoves.yml (optional)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Then run: python3 app_cipher_memory.py" -ForegroundColor Yellow