#!/bin/bash

# PMOVES Agent Setup Script
# Unified setup script for PMOVES agent configurations with feature flags

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Configuration mappings
declare -A FEATURE_FLAGS=(
    ["basic"]=""
    ["pro"]="PMOVES_FEATURE_PRO"
    ["mini"]="PMOVES_FEATURE_MINI"
    ["pro-plus"]="PMOVES_FEATURE_PRO_PLUS"
    ["full"]="PMOVES_FEATURE_PRO PMOVES_FEATURE_MINI PMOVES_FEATURE_PRO_PLUS"
)

declare -A COMPOSE_FILES=(
    ["basic"]="core/docker-compose/base.yml"
    ["pro"]="core/docker-compose/base.yml features/pro/docker-compose.yml"
    ["mini"]="core/docker-compose/base.yml features/mini/docker-compose.yml"
    ["pro-plus"]="core/docker-compose/base.yml features/pro-plus/docker-compose.yml"
    ["full"]="core/docker-compose/base.yml features/pro/docker-compose.yml features/mini/docker-compose.yml features/pro-plus/docker-compose.yml"
)

# Functions
write_header() {
    echo -e "\n${CYAN}=== $1 ===${NC}"
}

write_step() {
    echo -e "  ${YELLOW}→${NC} $1"
}

write_success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

write_error() {
    echo -e "  ${RED}✗${NC} $1"
}

check_prerequisites() {
    write_step "Checking prerequisites..."

    # Check if docker is available
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        write_success "Docker found: $DOCKER_VERSION"
    else
        write_error "Docker not found. Please install Docker."
        exit 1
    fi

    # Check if docker-compose is available
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version)
        write_success "Docker Compose found: $COMPOSE_VERSION"
    else
        write_error "Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
}

copy_env_files() {
    local features=("$@")
    write_step "Setting up environment files..."

    # Always copy core env
    if [ ! -f ".env" ]; then
        if [ "$DRY_RUN" = "true" ]; then
            echo -e "  ${GRAY}Would copy core/example.env to .env${NC}"
        else
            cp core/example.env .env
            write_success "Created .env from core/example.env"
        fi
    else
        write_success ".env already exists"
    fi

    # Copy feature-specific env files
    for feature in "${features[@]}"; do
        feature_name=$(echo "$feature" | sed 's/PMOVES_FEATURE_//' | tr '[:upper:]' '[:lower:]')
        env_file="features/$feature_name/example.env"

        if [ -f "$env_file" ]; then
            if [ "$DRY_RUN" = "true" ]; then
                echo -e "  ${GRAY}Would append $env_file to .env${NC}"
            else
                echo -e "\n# ===== $feature_name features =====" >> .env
                cat "$env_file" >> .env
                write_success "Added $feature_name environment variables"
            fi
        fi
    done
}

set_feature_flags() {
    local features=("$@")
    write_step "Setting feature flags..."

    for feature in "${features[@]}"; do
        if [ "$DRY_RUN" = "true" ]; then
            echo -e "  ${GRAY}Would set $feature=true${NC}"
        else
            # Add to .env if not already present
            if ! grep -q "^$feature=true" .env 2>/dev/null; then
                echo "$feature=true" >> .env
                write_success "Enabled $feature"
            else
                write_success "$feature already enabled"
            fi
        fi
    done
}

show_docker_command() {
    local compose_files=("$@")
    write_step "Docker Compose command:"
    local compose_args=""
    for file in "${compose_files[@]}"; do
        compose_args="$compose_args -f $file"
    done
    echo -e "  ${GRAY}docker compose$compose_args up -d${NC}"
}

start_services() {
    local compose_files=("$@")

    if [ "$DRY_RUN" = "true" ]; then
        show_docker_command "${compose_files[@]}"
        return
    fi

    write_step "Starting services..."

    local compose_args=""
    for file in "${compose_files[@]}"; do
        compose_args="$compose_args -f $file"
    done

    if docker compose $compose_args up -d; then
        write_success "Services started successfully"
    else
        write_error "Failed to start services"
        exit 1
    fi
}

# Parse arguments
CONFIG="basic"
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [-c|--config CONFIG] [--dry-run]"
            echo "Configurations: basic, pro, mini, pro-plus, full"
            exit 0
            ;;
        *)
            write_error "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Validate config
if [[ ! -v FEATURE_FLAGS[$CONFIG] ]]; then
    write_error "Invalid configuration: $CONFIG"
    echo "Available configurations: basic, pro, mini, pro-plus, full"
    exit 1
fi

# Main execution
write_header "PMOVES Agent Setup - Config: $CONFIG"

if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
fi

check_prerequisites

# Parse features and compose files
IFS=' ' read -r -a selected_features <<< "${FEATURE_FLAGS[$CONFIG]}"
IFS=' ' read -r -a selected_compose_files <<< "${COMPOSE_FILES[$CONFIG]}"

write_step "Configuration: $CONFIG"
write_step "Features: ${selected_features[*]:-none}"
write_step "Compose files: ${selected_compose_files[*]:-none}"

copy_env_files "${selected_features[@]}"
set_feature_flags "${selected_features[@]}"
start_services "${selected_compose_files[@]}"

write_header "Setup Complete"
echo -e "${GREEN}Your PMOVES agent is configured for: $CONFIG${NC}"
echo -e "${GRAY}Check the logs with: docker compose logs -f${NC}"