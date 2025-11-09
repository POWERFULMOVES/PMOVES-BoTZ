# PMOVES MCP Environment Verification Script (PowerShell)
# This script verifies that all required environment variables are properly configured

Write-Host "=== PMOVES MCP Environment Variable Verification ===" -ForegroundColor Cyan
Write-Host ""

# Function to check if variable exists and is not empty
function Check-Var {
    param(
        [string]$VarName
    )
    
    $varValue = [System.Environment]::GetEnvironmentVariable($VarName)
    
    if ([string]::IsNullOrEmpty($varValue)) {
        Write-Host "❌ $VarName is not set or empty" -ForegroundColor Red
        return $false
    } else {
        Write-Host "✅ $VarName is set" -ForegroundColor Green
        return $true
    }
}

# Function to check if variable exists in docker-compose
function Check-DockerComposeVar {
    param(
        [string]$VarName
    )
    
    $file = "docker-compose.mcp-pro.yml"
    
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        if ($content -match "\`$\{$VarName\}") {
            Write-Host "✅ $VarName is referenced in docker-compose.mcp-pro.yml" -ForegroundColor Green
            return $true
        } else {
            Write-Host "⚠️  $VarName is not referenced in docker-compose.mcp-pro.yml" -ForegroundColor Yellow
            return $false
        }
    } else {
        Write-Host "❌ docker-compose.mcp-pro.yml not found" -ForegroundColor Red
        return $false
    }
}

Write-Host "Loading environment from files..."
Write-Host ""

# Load environment from .env files
$envFiles = @(".env", ".env.local", "env.shared")

foreach ($file in $envFiles) {
    if (Test-Path $file) {
        Write-Host "Loading environment from $file..."
        Get-Content $file | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim()
                
                # Skip comments and empty lines
                if (-not $name.StartsWith('#') -and $name -ne '') {
                    [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
                }
            }
        }
    }
}

Write-Host ""
Write-Host "Checking required environment variables..."
Write-Host ""

# Required variables for MCP services
$requiredVars = @(
    "OPENAI_API_KEY",
    "VENICE_API_KEY", 
    "TAILSCALE_AUTHKEY",
    "E2B_API_KEY",
    "PMOVES_ROOT"
)

# Check each required variable
$allVarsSet = $true
foreach ($var in $requiredVars) {
    if (-not (Check-Var $var)) {
        $allVarsSet = $false
    }
}

Write-Host ""
Write-Host "Checking docker-compose configuration..."
Write-Host ""

# Check if variables are properly referenced in docker-compose
foreach ($var in $requiredVars) {
    Check-DockerComposeVar $var
}

Write-Host ""
Write-Host "=== Verification Summary ==="
Write-Host ""

if ($allVarsSet) {
    Write-Host "✅ All required environment variables are set!" -ForegroundColor Green
} else {
    Write-Host "❌ Some environment variables are missing. Please check the configuration." -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Next Steps ==="
Write-Host ""
Write-Host "1. If any variables are missing, add them to the appropriate .env file"
Write-Host "2. Restart the MCP services with:"
Write-Host "   docker-compose -f docker-compose.mcp-pro.yml down"
Write-Host "   docker-compose -f docker-compose.mcp-pro.yml up -d"
Write-Host ""
Write-Host "3. Check service logs to verify everything is working:"
Write-Host "   docker-compose -f docker-compose.mcp-pro.yml logs tailscale"
Write-Host "   docker-compose -f docker-compose.mcp-pro.yml logs mcp-gateway"
Write-Host "   docker-compose -f docker-compose.mcp-pro.yml logs cipher-memory"
Write-Host ""