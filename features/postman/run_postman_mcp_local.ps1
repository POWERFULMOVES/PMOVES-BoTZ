# Postman MCP Local Service Runner (PowerShell)
# This script runs Postman MCP Local service as a stdio-based MCP server
# 
# Usage: .\run_postman_mcp_local.ps1
# 
# The service will start and wait for MCP client connections via stdio
# This is the correct way to run stdio-based MCP servers

# Colors for output
$ErrorColor = "Red"
$SuccessColor = "Green"
$WarningColor = "Yellow"
$InfoColor = "Cyan"

Write-Host "========================================" -ForegroundColor $InfoColor
Write-Host "Postman MCP Local Service Runner" -ForegroundColor $InfoColor
Write-Host "========================================" -ForegroundColor $InfoColor

# Check if POSTMAN_API_KEY is set
if (-not $env:POSTMAN_API_KEY) {
    Write-Host "Error: POSTMAN_API_KEY environment variable is not set" -ForegroundColor $ErrorColor
    Write-Host "Please set POSTMAN_API_KEY environment variable:" -ForegroundColor $WarningColor
    Write-Host "`$env:POSTMAN_API_KEY = 'your_api_key_here'" -ForegroundColor $WarningColor
    exit 1
}

# Check if POSTMAN_API_BASE_URL is set
if (-not $env:POSTMAN_API_BASE_URL) {
    Write-Host "Warning: POSTMAN_API_BASE_URL not set, using default" -ForegroundColor $WarningColor
    $env:POSTMAN_API_BASE_URL = "https://api.postman.com"
}

Write-Host "Configuration:" -ForegroundColor $SuccessColor

# Safely display API key (first 10 chars)
if ($env:POSTMAN_API_KEY.Length -gt 10) {
    $keyDisplay = "$($env:POSTMAN_API_KEY.Substring(0, 10))..."
} else {
    $keyDisplay = "$($env:POSTMAN_API_KEY)..."
}
Write-Host "  POSTMAN_API_KEY: $keyDisplay" -ForegroundColor $SuccessColor
Write-Host "  POSTMAN_API_BASE_URL: $env:POSTMAN_API_BASE_URL" -ForegroundColor $SuccessColor

Write-Host "`nStarting Postman MCP Local service..." -ForegroundColor $SuccessColor
Write-Host "Note: This is a stdio-based MCP server that waits for client connections" -ForegroundColor $WarningColor
Write-Host "The service will appear to hang - this is normal behavior" -ForegroundColor $WarningColor
Write-Host "Use Ctrl+C to stop the service`n" -ForegroundColor $WarningColor

# Run Postman MCP server
# Using npx to ensure we have the latest version
try {
    npx @postman/postman-mcp-server@latest --full
}
catch {
    Write-Host "Error running Postman MCP server: $_" -ForegroundColor $ErrorColor
    exit 1
}

Write-Host "`nPostman MCP Local service stopped" -ForegroundColor $InfoColor