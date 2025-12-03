# Stop PMOVES-BoTZ
$env:PMZ_NAMESPACE = "pmoves-botz"
docker-compose -f core/docker-compose/base.yml -f core/docker-compose/overlays/development.yml down
Write-Host "PMOVES-BoTZ stopped."
