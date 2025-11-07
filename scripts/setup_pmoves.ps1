#!/usr/bin/env pwsh

<#
.SYNOPSIS
    PMOVES Agent Setup Script
.DESCRIPTION
    Unified setup script for PMOVES agent configurations with feature flags
.PARAMETER Config
    Configuration type: basic, pro, mini, pro-plus, full
.PARAMETER DryRun
    Show what would be done without executing
.EXAMPLE
    .\setup_pmoves.ps1 -Config pro
    .\setup_pmoves.ps1 -Config full -DryRun
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("basic", "pro", "mini", "pro-plus", "full")]
    [string]$Config = "basic",

    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Configuration mappings
$FeatureFlags = @{
    "basic" = @()
    "pro" = @("PMOVES_FEATURE_PRO")
    "mini" = @("PMOVES_FEATURE_MINI")
    "pro-plus" = @("PMOVES_FEATURE_PRO_PLUS")
    "full" = @("PMOVES_FEATURE_PRO", "PMOVES_FEATURE_MINI", "PMOVES_FEATURE_PRO_PLUS")
}

$ComposeFiles = @{
    "basic" = @("core/docker-compose/base.yml")
    "pro" = @("core/docker-compose/base.yml", "features/pro/docker-compose.yml")
    "mini" = @("core/docker-compose/base.yml", "features/mini/docker-compose.yml")
    "pro-plus" = @("core/docker-compose/base.yml", "features/pro-plus/docker-compose.yml")
    "full" = @("core/docker-compose/base.yml", "features/pro/docker-compose.yml", "features/mini/docker-compose.yml", "features/pro-plus/docker-compose.yml")
}

function Write-Header {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host "  → $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "  ✗ $Message" -ForegroundColor Red
}

function Test-Prerequisites {
    Write-Step "Checking prerequisites..."

    # Check if docker is available
    try {
        $dockerVersion = docker --version 2>$null
        Write-Success "Docker found: $dockerVersion"
    } catch {
        Write-Error "Docker not found. Please install Docker Desktop."
        exit 1
    }

    # Check if docker-compose is available
    try {
        $composeVersion = docker compose version 2>$null
        Write-Success "Docker Compose found: $composeVersion"
    } catch {
        Write-Error "Docker Compose not found. Please install Docker Compose."
        exit 1
    }
}

function Copy-EnvFiles {
    param([string[]]$Features)

    Write-Step "Setting up environment files..."

    # Always copy core env
    if (!(Test-Path ".env")) {
        if ($DryRun) {
            Write-Host "  Would copy core/example.env to .env" -ForegroundColor Gray
        } else {
            Copy-Item "core/example.env" ".env"
            Write-Success "Created .env from core/example.env"
        }
    } else {
        Write-Success ".env already exists"
    }

    # Copy feature-specific env files
    foreach ($feature in $Features) {
        $featureName = $feature -replace "PMOVES_FEATURE_", "" | ForEach-Object { $_.ToLower() }
        $envFile = "features/$featureName/example.env"

        if (Test-Path $envFile) {
            if ($DryRun) {
                Write-Host "  Would append $envFile to .env" -ForegroundColor Gray
            } else {
                $envContent = Get-Content $envFile
                Add-Content ".env" "`n# ===== $featureName features ====="
                Add-Content ".env" $envContent
                Write-Success "Added $featureName environment variables"
            }
        }
    }
}

function Set-FeatureFlags {
    param([string[]]$Features)

    Write-Step "Setting feature flags..."

    foreach ($feature in $Features) {
        if ($DryRun) {
            Write-Host "  Would set $feature=true" -ForegroundColor Gray
        } else {
            # Add to .env if not already present
            $envContent = Get-Content ".env" -ErrorAction SilentlyContinue
            if ($envContent -notcontains "$feature=true") {
                Add-Content ".env" "$feature=true"
                Write-Success "Enabled $feature"
            } else {
                Write-Success "$feature already enabled"
            }
        }
    }
}

function Show-DockerCommand {
    param([string[]]$ComposeFiles)

    Write-Step "Docker Compose command:"
    $composeArgs = $ComposeFiles | ForEach-Object { "-f $_" }
    $command = "docker compose $($composeArgs -join ' ') up -d"
    Write-Host "  $command" -ForegroundColor Gray
}

function Start-Services {
    param([string[]]$ComposeFiles)

    if ($DryRun) {
        Show-DockerCommand $ComposeFiles
        return
    }

    Write-Step "Starting services..."

    $composeArgs = $ComposeFiles | ForEach-Object { "-f", $_ }
    try {
        & docker compose $composeArgs up -d
        Write-Success "Services started successfully"
    } catch {
        Write-Error "Failed to start services: $_"
        exit 1
    }
}

# Main execution
Write-Header "PMOVES Agent Setup - Config: $Config"

if ($DryRun) {
    Write-Host "DRY RUN MODE - No changes will be made" -ForegroundColor Magenta
}

Test-Prerequisites

$selectedFeatures = $FeatureFlags[$Config]
$selectedComposeFiles = $ComposeFiles[$Config]

Write-Step "Configuration: $Config"
Write-Step "Features: $(if ($selectedFeatures) { $selectedFeatures -join ', ' } else { 'none' })"
Write-Step "Compose files: $(if ($selectedComposeFiles) { $selectedComposeFiles -join ', ' } else { 'none' })"

Copy-EnvFiles $selectedFeatures
Set-FeatureFlags $selectedFeatures
Start-Services $selectedComposeFiles

Write-Header "Setup Complete"
Write-Host "Your PMOVES agent is configured for: $Config" -ForegroundColor Green
Write-Host "Check the logs with: docker compose logs -f" -ForegroundColor Gray