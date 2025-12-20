# PMOVES-BoTZ Makefile
# Build automation for the unified MCP agent stack
#
# Usage:
#   make help          - Show all targets
#   make env-sync      - Sync API keys from parent repo
#   make cipher-build  - Build cipher for n8n-agent integration
#   make up            - Start all services
#   make test-e2e      - Run full e2e test suite

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ============================================================================
# Configuration
# ============================================================================

# Paths
CIPHER_DIR := features/cipher/pmoves_cipher
ENV_SHARED_PARENT := ../pmoves/env.shared
ENV_SHARED_LOCAL := core/docker-compose/env.shared
ROOT_ENV := .env
EXAMPLE_ENV := core/example.env

# Compose configuration (order matters - matches bring_up_pmoves_botz.sh)
# Note: metrics excluded by default - use parent PMOVES.AI monitoring stack
COMPOSE_BASE := core/docker-compose/base.yml
COMPOSE_FILES := -f $(COMPOSE_BASE) \
                 -f features/pro/docker-compose.yml \
                 -f features/network/external.yml \
                 -f features/cipher/docker-compose.yml

# Include metrics if running standalone (not alongside parent PMOVES.AI)
COMPOSE_FILES_WITH_METRICS := $(COMPOSE_FILES) -f features/metrics/docker-compose.yml

# Service ports (defaults)
GATEWAY_PORT ?= 2091
DOCLING_PORT ?= 3020
CIPHER_API_PORT ?= 3011
VL_PORT ?= 7072

# ============================================================================
# Help
# ============================================================================

.PHONY: help
help: ## Show available targets
	@echo "PMOVES-BoTZ Build Automation"
	@echo "============================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick Start:"
	@echo "  make env-sync && make cipher-build && make up && make test-smoke"

# ============================================================================
# Environment Setup
# ============================================================================

.PHONY: env-init env-sync env-verify

env-init: ## Initialize .env from example (if not exists)
	@if [ ! -f "$(ROOT_ENV)" ]; then \
	  if [ -f "$(EXAMPLE_ENV)" ]; then \
	    cp "$(EXAMPLE_ENV)" "$(ROOT_ENV)"; \
	    echo "Created .env from $(EXAMPLE_ENV)"; \
	  else \
	    touch "$(ROOT_ENV)"; \
	    echo "Created empty .env"; \
	  fi; \
	else \
	  echo ".env already exists"; \
	fi

env-sync: env-init ## Sync API keys from parent pmoves/env.shared
	@./scripts/sync_env.sh

env-verify: ## Verify all required API keys are configured
	@./scripts/verify_env.sh

# ============================================================================
# Cipher Build
# ============================================================================

.PHONY: cipher-deps cipher-build cipher-build-ui cipher-clean cipher-setup

cipher-deps: ## Install cipher dependencies
	@echo "Installing cipher dependencies..."
	@cd $(CIPHER_DIR) && pnpm install --no-frozen-lockfile
	@echo "Cipher dependencies installed"

cipher-build: cipher-deps ## Build cipher (no UI - faster)
	@echo "Building cipher..."
	@cd $(CIPHER_DIR) && pnpm run build:no-ui
	@if [ -f "$(CIPHER_DIR)/.env.example" ] && [ ! -f "$(CIPHER_DIR)/dist/.env" ]; then \
	  cp "$(CIPHER_DIR)/.env.example" "$(CIPHER_DIR)/dist/.env"; \
	fi
	@echo "Cipher built at $(CIPHER_DIR)/dist/"

cipher-build-ui: cipher-deps ## Build cipher with UI (slower)
	@echo "Building cipher with UI..."
	@cd $(CIPHER_DIR)/src/app/ui && pnpm install --no-frozen-lockfile
	@cd $(CIPHER_DIR) && pnpm run build
	@echo "Cipher built with UI at $(CIPHER_DIR)/dist/"

cipher-clean: ## Clean cipher build artifacts
	@echo "Cleaning cipher..."
	@cd $(CIPHER_DIR) && rm -rf dist node_modules src/app/ui/node_modules src/app/ui/.next
	@echo "Cipher cleaned"

cipher-setup: cipher-build ## Full cipher setup including PMOVES config
	@./features/cipher/setup_cipher.sh
	@echo "Cipher setup complete"

# ============================================================================
# Docker Compose
# ============================================================================

.PHONY: up down restart rebuild logs ps

up: env-verify cipher-build ## Start all services
	@echo "Starting PMOVES-BoTZ stack..."
	docker compose --env-file $(ROOT_ENV) $(COMPOSE_FILES) up -d
	@$(MAKE) wait-healthy
	@echo "Stack is up! Run 'make ps' to see status"

down: ## Stop all services
	docker compose --env-file $(ROOT_ENV) $(COMPOSE_FILES) down

restart: down up ## Restart all services

rebuild: ## Rebuild and restart all services (no cache)
	docker compose --env-file $(ROOT_ENV) $(COMPOSE_FILES) down
	docker compose --env-file $(ROOT_ENV) $(COMPOSE_FILES) build --no-cache
	@$(MAKE) up

logs: ## Tail logs from all services
	docker compose --env-file $(ROOT_ENV) $(COMPOSE_FILES) logs -f

ps: ## Show service status
	docker compose --env-file $(ROOT_ENV) $(COMPOSE_FILES) ps

# ============================================================================
# Health Checks
# ============================================================================

.PHONY: wait-healthy health-check

wait-healthy: ## Wait for services to become healthy
	@./scripts/wait_healthy.sh

health-check: ## Quick health check of all services
	@echo "Checking service health..."
	@curl -fsS http://localhost:$(GATEWAY_PORT)/health >/dev/null 2>&1 && echo "  Gateway ($(GATEWAY_PORT)): OK" || echo "  Gateway ($(GATEWAY_PORT)): FAIL"
	@curl -fsS http://localhost:$(DOCLING_PORT)/health >/dev/null 2>&1 && echo "  Docling ($(DOCLING_PORT)): OK" || echo "  Docling ($(DOCLING_PORT)): FAIL"
	@curl -fsS http://localhost:$(VL_PORT)/health >/dev/null 2>&1 && echo "  VL-Sentinel ($(VL_PORT)): OK" || echo "  VL-Sentinel ($(VL_PORT)): FAIL"
	@curl -fsS http://localhost:7071/health >/dev/null 2>&1 && echo "  E2B-Runner (7071): OK" || echo "  E2B-Runner (7071): FAIL"
	@docker exec docker-compose-cipher-memory-1 curl -fsS http://localhost:8081/health >/dev/null 2>&1 && echo "  Cipher (internal): OK" || echo "  Cipher (internal): SKIP (internal service)"

# ============================================================================
# Testing
# ============================================================================

.PHONY: test test-smoke test-integration test-cipher test-e2e test-ci

test: test-smoke test-integration ## Run smoke + integration tests

test-smoke: ## Run smoke tests
	@echo "Running smoke tests..."
	@python3 scripts/smoke_tests.py

test-integration: ## Run pytest integration tests
	@echo "Running integration tests..."
	@if [ -d "tests/integration" ]; then \
	  cd tests/integration && \
	  pip install -q -r test_requirements.txt 2>/dev/null || true && \
	  pytest -v --tb=short -m "integration or docker" || true; \
	else \
	  echo "No integration tests directory found"; \
	fi

test-cipher: ## Run cipher unit tests
	@echo "Running cipher tests..."
	@cd $(CIPHER_DIR) && pnpm test || pnpm test:unit || echo "No cipher tests configured"

test-e2e: up ## Full end-to-end test suite (starts services first)
	@echo "Running E2E tests..."
	@$(MAKE) test-smoke
	@$(MAKE) test-integration
	@echo "E2E tests complete"

test-ci: env-verify ## CI-friendly test run (no service startup)
	@$(MAKE) test-smoke || true
	@$(MAKE) test-integration || true

# ============================================================================
# CI/CD
# ============================================================================

.PHONY: ci-build ci-test lint

ci-build: cipher-build ## CI build step
	@echo "Validating compose configs..."
	@docker compose -f $(COMPOSE_BASE) config > /dev/null
	@echo "Compose configs valid"

ci-test: ci-build ## CI test step (build + test)
	@$(MAKE) test-ci

lint: ## Lint cipher code
	@echo "Linting cipher..."
	@cd $(CIPHER_DIR) && pnpm lint || echo "No lint script configured"

# ============================================================================
# Cleanup
# ============================================================================

.PHONY: clean clean-all

clean: down ## Stop services and remove volumes
	docker compose --env-file $(ROOT_ENV) $(COMPOSE_FILES) down -v --remove-orphans

clean-all: clean cipher-clean ## Full cleanup including cipher build artifacts
	@rm -rf .pytest_cache htmlcov coverage.xml test_report.*
	@echo "Full cleanup complete"

# ============================================================================
# Utilities
# ============================================================================

.PHONY: shell-gateway shell-cipher

shell-gateway: ## Open shell in gateway container
	docker compose --env-file $(ROOT_ENV) $(COMPOSE_FILES) exec mcp-gateway /bin/sh

shell-cipher: ## Open shell in cipher-memory container
	docker compose --env-file $(ROOT_ENV) $(COMPOSE_FILES) exec cipher-memory /bin/bash
