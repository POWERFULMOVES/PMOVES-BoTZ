#!/usr/bin/env pwsh

param([Parameter(Mandatory=$true)][ValidateSet('up','down','rebuild','logs','health','metrics','provision-grafana-existing')]$Cmd,[string]$Service)

$ErrorActionPreference = "Stop"
$base = @('-f','core/docker-compose/base.yml','-f','features/pro/docker-compose.yml','-f','features/network/external.yml','-f','features/metrics/docker-compose.yml','-f','features/cipher/docker-compose.yml')

switch ($Cmd) {
  'up' { docker compose --env-file .env $base up -d }
  'down' { docker compose --env-file .env $base down }
  'rebuild' { docker compose --env-file .env -f core/docker-compose/base.yml build --no-cache docling-mcp }
  'logs' { docker compose $base logs -f $Service }
  'health' {
    try { iwr -UseBasicParsing http://localhost:($env:GATEWAY_PORT ?? '2091')/ready -TimeoutSec 10 | Out-Null; Write-Host 'Gateway OK' } catch { Write-Host 'Gateway FAIL' }
    try { iwr -UseBasicParsing http://localhost:($env:DOCLING_PORT ?? '3020')/health -TimeoutSec 10 | Out-Null; Write-Host 'Docling OK' } catch { Write-Host 'Docling FAIL' }
  }
  'metrics' {
    try { iwr -UseBasicParsing http://localhost:($env:PROMETHEUS_PORT ?? '9090')/targets -TimeoutSec 10 | Select-Object -First 10 } catch { $_ }
  }
  'provision-grafana-existing' { ./scripts/grafana_provision.ps1 -GrafanaUrl http://localhost:3002 -PromUrl http://host.docker.internal:9090 }
}

