Param([Parameter(Mandatory=$true)][string]$TS_AUTHKEY)
$env:TS_AUTHKEY = $TS_AUTHKEY
docker compose -f ./docker-compose.pmoves-mini.yml up -d --remove-orphans
Write-Host "==> MCP Gateway local: http://127.0.0.1:2091/mcp"
Write-Host "==> Check Tailscale logs for your HTTPS URL."