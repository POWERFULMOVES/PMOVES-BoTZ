# Start PMOVES-BoTZ
$env:PMZ_NAMESPACE = "pmoves-botz"
docker-compose -f core/docker-compose/base.yml -f core/docker-compose/overlays/development.yml up -d
Write-Host "PMOVES-BoTZ started."
Write-Host "Gateway: http://localhost:2091"
Write-Host "Docling: http://localhost:3020"
Write-Host "E2B: http://localhost:7071"
Write-Host "VL Sentinel: http://localhost:7072"
