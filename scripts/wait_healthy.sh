#!/usr/bin/env bash
# Wait for PMOVES-BoTZ services to become healthy
#
# Usage: ./scripts/wait_healthy.sh
#
# Polls service health endpoints until all are healthy or timeout is reached.

set -euo pipefail

# Configuration
TIMEOUT=${WAIT_TIMEOUT:-120}
INTERVAL=${WAIT_INTERVAL:-5}

# Service endpoints to check (name:port:path)
SERVICES=(
    "Gateway:2091:/ready"
    "Docling:3020:/health"
    "Cipher-API:3011:/health"
    "VL-Sentinel:7072:/health"
)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Waiting for services to become healthy (timeout: ${TIMEOUT}s)..."
echo ""

start_time=$(date +%s)

check_service() {
    local name="$1"
    local port="$2"
    local path="$3"
    curl -fsS --max-time 5 "http://localhost:${port}${path}" >/dev/null 2>&1
}

# Track which services are healthy
declare -A service_status

while true; do
    elapsed=$(($(date +%s) - start_time))

    if [[ $elapsed -ge $TIMEOUT ]]; then
        echo ""
        echo -e "${RED}Timeout waiting for services after ${TIMEOUT}s${NC}"
        echo ""
        echo "Status:"
        for service in "${SERVICES[@]}"; do
            IFS=':' read -r name port path <<< "$service"
            status="${service_status[$name]:-unhealthy}"
            if [[ "$status" == "healthy" ]]; then
                echo -e "  ${GREEN}[OK]${NC}   $name (port $port)"
            else
                echo -e "  ${RED}[FAIL]${NC} $name (port $port)"
            fi
        done
        exit 1
    fi

    healthy_count=0
    total_count=${#SERVICES[@]}

    for service in "${SERVICES[@]}"; do
        IFS=':' read -r name port path <<< "$service"

        if check_service "$name" "$port" "$path"; then
            service_status[$name]="healthy"
            ((healthy_count++))
        else
            service_status[$name]="unhealthy"
        fi
    done

    if [[ $healthy_count -eq $total_count ]]; then
        echo ""
        echo -e "${GREEN}All services healthy!${NC}"
        echo ""
        echo "Service URLs:"
        for service in "${SERVICES[@]}"; do
            IFS=':' read -r name port path <<< "$service"
            echo "  - $name: http://localhost:$port"
        done
        exit 0
    fi

    # Progress indicator
    printf "\r  %d/%d services healthy (${elapsed}s elapsed)..." "$healthy_count" "$total_count"
    sleep "$INTERVAL"
done
