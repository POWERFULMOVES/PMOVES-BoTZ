#!/bin/bash
# Unified start script for PMOVES-BoTZ

OVERLAY=${1:-development}

COMPOSE_FILES=(
    "core/docker-compose/base.yml"
    "core/docker-compose/overlays/${OVERLAY}.yml"
)

docker-compose -f "${COMPOSE_FILES[@]}" up -d
