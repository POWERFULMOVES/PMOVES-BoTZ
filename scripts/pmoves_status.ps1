#!/usr/bin/env pwsh

$ns = $env:PMZ_NAMESPACE; if (-not $ns) { $ns = $env:COMPOSE_PROJECT_NAME }; if (-not $ns) { $ns = 'pmoves-botz' }
$mode = if ($env:PMZ_INTERNAL_ONLY -eq '1') { 'internal-only' } elseif ($env:PMZ_EPHEMERAL -eq '1') { 'ephemeral' } else { 'normal' }

Write-Host "PMOVES-BotZ Status"
Write-Host "- Namespace: $ns"
Write-Host "- Port mode: $mode"
Write-Host "- pmoves-net: $($env:PMOVES_AI_NETWORK ?? 'pmoves-net')"

function Get-HostPort([string]$svc,[string]$cport) {
  $name = "$ns-$svc-1"
  try {
    $obj = docker inspect $name | ConvertFrom-Json
    $hp = $obj[0].NetworkSettings.Ports."$cport/tcp"[0].HostPort
    return $hp
  } catch { return $null }
}

Write-Host "`nEndpoints (host):"
$gw = $env:GATEWAY_PORT; if (-not $gw) { $gw = Get-HostPort 'mcp-gateway' '8000' }; Write-Host ("Gateway`.  http://localhost:{0}/ready" -f $gw)
$dl = $env:DOCLING_PORT; if (-not $dl) { $dl = Get-HostPort 'docling-mcp' '3020' }; Write-Host ("Docling`. http://localhost:{0}/health" -f $dl)
$cp = $env:CIPHER_API_PORT; if (-not $cp) { $cp = Get-HostPort 'cipher-memory' '3011' }; if ($cp) { Write-Host ("Cipher`.  http://localhost:{0}/health" -f $cp) }

Write-Host "`nEndpoints (pmoves-net DNS):"
Write-Host "Gateway`.  http://mcp-gateway:8000"
Write-Host "Docling`. http://docling-mcp:3020"
Write-Host "Cipher`.  http://cipher-memory:3011"
Write-Host "E2B`.     http://e2b-runner:7071"
Write-Host "VL`.      http://vl-sentinel:7072"

Write-Host "`nAutodiscovered blackbox targets:"
$fd = "features/metrics/file_sd/blackbox_targets.yml"
if (Test-Path $fd) { Get-Content $fd } else { Write-Host "(none yet)" }

