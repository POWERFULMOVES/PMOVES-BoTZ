# Unified start script for PMOVES-BoTZ

param (
    [string]$Overlay = "development"
)

$ComposeFiles = @(
    "core/docker-compose/base.yml",
    "core/docker-compose/overlays/$($Overlay).yml"
)

docker-compose -f $ComposeFiles up -d
