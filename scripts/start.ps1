# Start PMOVES-BoTZ
$env:PMZ_NAMESPACE = "pmoves-botz"
$env:COMPOSE_PROJECT_NAME = "pmoves-botz"

# Use base.windows.yml for Windows compatibility (disables Linux-only services like Tailscale)
# --env-file ensures credentials are loaded from root .env
docker compose --env-file .env -f core/docker-compose/base.yml -f core/docker-compose/base.windows.yml -f core/docker-compose/overlays/development.yml up -d

Write-Host ""
Write-Host "PMOVES-BoTZ started." -ForegroundColor Green
Write-Host ""
Write-Host "Services:"
Write-Host "  Gateway:     http://localhost:2091"
Write-Host "  TensorZero:  http://localhost:3006"
Write-Host "  Cipher:      http://localhost:8081"
Write-Host "  Docling:     http://localhost:3020"
Write-Host "  E2B:         http://localhost:7071"
Write-Host "  VL Sentinel: http://localhost:7072"
Write-Host ""
Write-Host "GPU: Routes to Ollama on host (http://host.docker.internal:11434)"
