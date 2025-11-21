#!/usr/bin/env pwsh

param(
  [string]$GrafanaUrl = "http://localhost:3002",
  [string]$GrafanaUser = "admin",
  [string]$GrafanaPass = "admin",
  [string]$PromUrl = "http://host.docker.internal:9090"
)

$ErrorActionPreference = "Stop"

function Invoke-Grafana {
  param([string]$Method, [string]$Path, [string]$Body = "")
  $uri = "$GrafanaUrl$Path"
  $headers = @{ Authorization = ("Basic {0}" -f [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$GrafanaUser`:$GrafanaPass"))) }
  if ($Body) {
    Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -ContentType 'application/json' -Body $Body
  } else {
    Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
  }
}

Write-Host "Creating Prometheus datasource 'host-prom' at $PromUrl ..."
try {
  Invoke-Grafana -Method POST -Path "/api/datasources" -Body (@{
    name = "host-prom"; type = "prometheus"; access = "proxy"; url = $PromUrl; isDefault = $false
  } | ConvertTo-Json -Compress)
} catch { }

$dashPath = Join-Path (Split-Path -Parent $PSCommandPath) "..\features\metrics\grafana\dashboards\pmoves_overview.json"
$dashJson = Get-Content $dashPath -Raw
$import = @{ dashboard = ($dashJson | ConvertFrom-Json | ConvertTo-Json -Compress | ConvertFrom-Json); overwrite = $true; inputs = @(@{ name='__DS_PROM__'; type='datasource'; pluginId='prometheus'; value='host-prom' }); folderId = 0 } | ConvertTo-Json -Depth 6

Write-Host "Importing PMOVES Overview dashboard ..."
Invoke-Grafana -Method POST -Path "/api/dashboards/import" -Body $import | Out-Null

$healthPath = Join-Path (Split-Path -Parent $PSCommandPath) "..\features\metrics\grafana\dashboards\pmoves_services_health.json"
$healthJson = Get-Content $healthPath -Raw
$import2 = @{ dashboard = ($healthJson | ConvertFrom-Json | ConvertTo-Json -Compress | ConvertFrom-Json); overwrite = $true; inputs = @(@{ name='__DS_PROM__'; type='datasource'; pluginId='prometheus'; value='host-prom' }); folderId = 0 } | ConvertTo-Json -Depth 6
Write-Host "Importing PMOVES Services Health dashboard ..."
Invoke-Grafana -Method POST -Path "/api/dashboards/import" -Body $import2 | Out-Null

Write-Host "Provisioning complete. Open $GrafanaUrl and search for 'PMOVES Overview' and 'PMOVES Services Health'."
