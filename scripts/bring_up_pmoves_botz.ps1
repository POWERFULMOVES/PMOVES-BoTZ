#!/usr/bin/env pwsh

param(
  [string]$Namespace = "botz-dev",
  [string]$PrometheusPort = "9090",
  [string]$GrafanaPort = "3033",
  [string]$AlertmanagerPort = "9093"
)

$ErrorActionPreference = "Stop"
$env:PMZ_NAMESPACE = $Namespace
if (-not $env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME = $Namespace }
if (-not $env:PMOVES_AI_NETWORK) { $env:PMOVES_AI_NETWORK = 'pmoves-net' }

# Local-first bootstrap: ensure a root .env exists so users don't need to cd around
if (-not (Test-Path ".env")) {
  Write-Host "[0/4] No .env found at repo root — bootstrapping from examples (local-first, Ollama)…"
  try {
    # Prefer the setup script if present (will merge feature example.env files)
    if (Test-Path "./scripts/setup_pmoves.ps1") {
      ./scripts/setup_pmoves.ps1 -Config pro -Namespace $Namespace | Out-Null
    } elseif (Test-Path "./core/example.env") {
      Copy-Item ./core/example.env ./.env
    }
    Write-Host "Created .env. You can edit it later to add API keys."
  } catch {
    Write-Warning "Failed to auto-create .env; continuing with process env only."
  }
}

if (-not $env:GATEWAY_PORT) { $env:GATEWAY_PORT = '2091' }
if (-not $env:DOCLING_PORT) { $env:DOCLING_PORT = '3020' }
if (-not $env:E2B_PORT) { $env:E2B_PORT = '7071' }
if (-not $env:VL_PORT) { $env:VL_PORT = '7072' }
$env:CRUSH_PORT = if ($env:CRUSH_PORT) { $env:CRUSH_PORT } else { '7069' }
$env:PROMETHEUS_PORT = $PrometheusPort
$env:GRAFANA_PORT = $GrafanaPort
$env:ALERTMANAGER_PORT = $AlertmanagerPort
$env:CIPHER_UI_PORT = if ($env:CIPHER_UI_PORT) { $env:CIPHER_UI_PORT } else { '3010' }
$env:CIPHER_API_PORT = if ($env:CIPHER_API_PORT) { $env:CIPHER_API_PORT } else { '3011' }

# Local-first defaults: prefer Ollama on the developer host.
if (-not $env:VL_PROVIDER) { $env:VL_PROVIDER = 'ollama' }
if (-not $env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL = 'http://host.docker.internal:11434' }
Write-Host ("Local-first mode: VL_PROVIDER={0}, OLLAMA_BASE_URL={1}" -f $env:VL_PROVIDER, $env:OLLAMA_BASE_URL)

# Friendly heads-up for optional external deps
if (-not $env:E2B_API_KEY) { Write-Host "Note: E2B_API_KEY not set; e2b-runner health may be 'unhealthy' until provided." }
if (-not $env:VENICE_API_KEY) { Write-Host "Note: VENICE_API_KEY not set; cipher-memory may restart until provided." }

Write-Host "[1/4] Rebuilding Docling MCP (no cache) ..."
docker compose --env-file .env -f core/docker-compose/base.yml build --no-cache docling-mcp | Out-Null

Write-Host "[2/4] Starting PMOVES-BotZ core + pro + metrics on '$Namespace' (network: $env:PMOVES_AI_NETWORK) ..."

# Build compose args with optional port-mode overlays
$composeArgs = @(
  '-f','core/docker-compose/base.yml',
  '-f','features/pro/docker-compose.yml',
  '-f','features/network/external.yml',
  '-f','features/metrics/docker-compose.yml',
  '-f','features/cipher/docker-compose.yml'
)

if ($env:PMZ_INTERNAL_ONLY -eq '1') {
  Write-Host "Applying internal-only overlay (no host ports)"
  $composeArgs += @('-f','features/network/internal.yml')
} elseif ($env:PMZ_EPHEMERAL -eq '1') {
  Write-Host "Applying ephemeral overlay (random host ports)"
  $composeArgs += @('-f','features/network/ephemeral.yml')
}

docker compose --env-file .env $composeArgs up -d | Out-Null

Write-Host "[3/4] Checking health ..."
Start-Sleep -Seconds 5
try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 http://localhost:$env:GATEWAY_PORT/metrics | Out-Null; Write-Host "Gateway OK" } catch { Write-Host "Gateway not ready" }
try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 http://localhost:$env:DOCLING_PORT/health | Out-Null; Write-Host "Docling OK" } catch { Write-Host "Docling not ready" }

Write-Host "[4/4] Autodiscover Prometheus targets and reload ..."
try { python ./scripts/prom_autodiscover.py | Out-Null } catch { Write-Host "Autodiscovery failed" }

Write-Host "Provision existing Grafana (3002) if reachable ..."
try {
  Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://localhost:3002/login | Out-Null
  ./scripts/grafana_provision.ps1 -GrafanaUrl http://localhost:3002 -PromUrl http://host.docker.internal:9090 | Out-Null
} catch {
  Write-Host "grafana-1 (3002) not reachable; skipping external provisioning"
}

Write-Host "Done. Prometheus: http://localhost:$env:PROMETHEUS_PORT Grafana: http://localhost:$env:GRAFANA_PORT"
