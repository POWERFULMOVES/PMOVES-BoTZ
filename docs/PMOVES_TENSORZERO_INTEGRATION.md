# PMOVES-TensorZero Integration Patterns

**Status:** Tracking PMOVES-tensorzero PR #1 (not yet merged)
**Last Updated:** 2026-01-29

This document describes integration patterns from PMOVES-tensorzero that should be adopted by PMOVES-BoTZ for consistent infrastructure across the PMOVES.AI ecosystem.

---

## 1. CHIT Secrets Management

CHIT (Compressed Hierarchical Injected Tokens) provides centralized secrets management with precedence-based resolution.

### Configuration File

Location: `chit/secrets_manifest_v2.yaml`

```yaml
api_version: "2.0"
environment: ${CHIT_ENVIRONMENT:-production}

sources:
  # Environment variables (base precedence)
  - type: env
    precedence: 50

  # CHIT Vault (highest precedence - overrides env vars)
  - type: chit_vault
    precedence: 100
    endpoint: ${CHIT_VAULT_ENDPOINT:-http://chit-vault:8050}

variables:
  - SERVICE_NAME
  - SERVICE_SLUG
  - NATS_URL
  # Add service-specific secrets as needed

groups:
  development:
    required: [SERVICE_NAME, NATS_URL]
    optional: [LOG_LEVEL]
  production:
    required: [SERVICE_NAME, SERVICE_SLUG, NATS_URL]

validation:
  strict: false
  fail_on_missing_required: true
```

### Precedence Order

| Source | Precedence | Description |
|--------|------------|-------------|
| Environment Variables | 50 | Static overrides from `.env` or container env |
| CHIT Vault | 100 | Runtime secrets from centralized vault |

Higher precedence values override lower ones. CHIT Vault secrets take priority over environment variables.

---

## 2. Tier-Based Environment Loading

PMOVES uses a tiered environment configuration system for consistent service configuration across different deployment contexts.

### File Structure

```
project-root/
  env.shared           # Base PMOVES.AI service configuration
  env.tier-agent.sh    # Agent tier specific variables
  env.tier-llm.sh      # LLM tier specific variables
  env.tier-data.sh     # Data tier specific variables
```

### env.shared (Base Configuration)

Contains common environment variables shared across all tiers:

```bash
# Environment identifier
export PMOVES_ENV=${PMOVES_ENV:-production}
export TIER=${TIER:-agent}

# Service identity
export SERVICE_NAME=${SERVICE_NAME:-botz-framework}
export SERVICE_SLUG=${SERVICE_SLUG:-botz-framework}

# NATS
export NATS_URL=${NATS_URL:-nats://nats:4222}

# TensorZero Gateway
export TENSORZERO_URL=${TENSORZERO_URL:-http://tensorzero-gateway:3030}

# Data Services
export QDRANT_URL=${QDRANT_URL:-http://qdrant:6333}
export MEILISEARCH_URL=${MEILISEARCH_URL:-http://meilisearch:7700}

# Health Configuration
export HEALTH_CHECK_PATH=${HEALTH_CHECK_PATH:-/healthz}
export HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-30}
```

### env.tier-agent.sh (Agent Tier)

Agent-specific configuration layered on top of shared:

```bash
# Source base config first
# source env.shared && source env.tier-agent.sh

export TIER=agent

# Agent limits
export MAX_CONCURRENT_AGENTS=${MAX_CONCURRENT_AGENTS:-50}
export AGENT_TIMEOUT_MS=${AGENT_TIMEOUT_MS:-300000}

# MCP configuration
export MCP_ENABLED=${MCP_ENABLED:-true}
export MCP_TIMEOUT_MS=${MCP_TIMEOUT_MS:-30000}

# LLM defaults
export DEFAULT_MODEL=${DEFAULT_MODEL:-claude-sonnet-4-5}
export DEFAULT_TEMPERATURE=${DEFAULT_TEMPERATURE:-0.7}
```

### Docker Compose YAML Anchors

Use YAML anchors for DRY tier-based env loading:

```yaml
x-env-shared: &env-shared
  PMOVES_ENV: ${PMOVES_ENV:-production}
  NATS_URL: ${NATS_URL:-nats://nats:4222}
  TENSORZERO_URL: ${TENSORZERO_URL:-http://tensorzero-gateway:3030}

x-env-agent: &env-agent
  <<: *env-shared
  TIER: agent
  MAX_CONCURRENT_AGENTS: ${MAX_CONCURRENT_AGENTS:-50}
  MCP_ENABLED: ${MCP_ENABLED:-true}

x-env-llm: &env-llm
  <<: *env-shared
  TIER: llm
  DEFAULT_MODEL: ${DEFAULT_MODEL:-claude-sonnet-4-5}
  TENSORZERO_CLICKHOUSE_URL: ${TENSORZERO_CLICKHOUSE_URL:-http://tensorzero-clickhouse:8123}

services:
  agent-zero:
    environment:
      <<: *env-agent
      SERVICE_NAME: agent-zero

  tensorzero-gateway:
    environment:
      <<: *env-llm
      SERVICE_NAME: tensorzero-gateway
```

---

## 3. Service Discovery

### Overview

PMOVES implements a fallback chain for service discovery:

1. **Environment Variables** - Static overrides (highest priority)
2. **Supabase** - Dynamic service catalog
3. **NATS Announcements** - Real-time service discovery
4. **Docker DNS** - Development fallback (lowest priority)

### Service Announcer Module

Location: `pmoves_announcer/`

Services announce their availability via NATS on startup:

```python
from pmoves_announcer import ServiceAnnouncer, announce_service

# Simple announcement
await announce_service(
    slug="my-service",
    name="My Service",
    url="http://my-service:8080",
    port=8080,
    tier="api",
    metadata={"features": ["mcp", "health"]}
)

# Background announcer (periodic re-announcements)
announcer = ServiceAnnouncer(slug="my-service", ...)
bg = BackgroundAnnouncer(announcer, interval=60)
await bg.start()
```

NATS Subject: `services.announce.v1`

### Service Registry Client

Location: `pmoves_registry/`

Resolves service URLs using the fallback chain:

```python
from pmoves_registry import get_service_url, get_service_info

# Simple URL resolution
url = await get_service_url("hirag-v2")
# Returns: http://hi-rag-gateway-v2:8086

# Full service info
info = await get_service_info("agent-zero", default_port=8080)
print(info.base_url)         # http://agent-zero:8080
print(info.health_check_url) # http://agent-zero:8080/healthz
```

### Environment Variable Resolution

The registry checks multiple patterns for environment overrides:

| Slug | Checked Variables |
|------|-------------------|
| `hirag-v2` | `HIRAG_V2_URL`, `HIRAGV2_URL`, `HIRAG-V2_URL` |
| `agent-zero` | `AGENT_ZERO_URL`, `AGENTZERO_URL` |

---

## 4. Health Endpoints

### Overview

Location: `pmoves_health/`

Standard health check module providing:
- Consistent `/healthz` endpoint across all services
- Dependency health checks (database, HTTP, NATS)
- Degraded state reporting

### Usage

```python
from pmoves_health import HealthChecker, add_nats_check, add_http_check

# Create checker
checker = HealthChecker("my-service")

# Add dependency checks
checker.nats("nats://nats:4222")
checker.http("http://tensorzero:3030/healthz", name="tensorzero")

# Custom check
async def check_memory():
    import psutil
    return psutil.virtual_memory().percent < 90
checker.add_custom_check("memory_ok", check_memory)

# Run checks
status = await checker.check_all()
```

### FastAPI Integration

```python
from fastapi import FastAPI
from pmoves_health import health_check_router

app = FastAPI()
app.include_router(health_check_router)
# Exposes GET /healthz
```

### Health Response Format

```json
{
  "status": "healthy",
  "service": "my-service",
  "timestamp": "2026-01-29T12:00:00Z",
  "nats_connected": true,
  "tensorzero_connected": true,
  "memory_ok": true
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `healthy` | All required checks pass |
| `degraded` | Optional checks failing, required checks pass |
| `unhealthy` | One or more required checks failing |

---

## 5. Integration Status

### PMOVES-tensorzero PR #1

**Status:** Open (not yet merged)

This PR introduces the integration patterns described in this document. BoTZ has implemented compatible versions of these modules:

| Module | BoTZ Location | Status |
|--------|---------------|--------|
| CHIT Secrets | `chit/secrets_manifest_v2.yaml` | Implemented |
| env.shared | `env.shared` | Implemented |
| env.tier-agent | `env.tier-agent.sh` | Implemented |
| Service Announcer | `pmoves_announcer/` | Implemented |
| Service Registry | `pmoves_registry/` | Implemented |
| Health Module | `pmoves_health/` | Implemented |

### Action Items

1. **Track PR #1** - Monitor PMOVES-tensorzero for merge status
2. **Sync Updates** - After merge, verify BoTZ modules match upstream patterns
3. **Add Supabase Backend** - Implement Supabase service catalog lookup in registry
4. **Add NATS Cache** - Implement NATS announcement caching in registry

---

## Related Documentation

- [Architecture Overview](./ARCHITECTURE_BOTZ.md) - BoTZ system architecture
- [Network Tier Segmentation](./network-tier-segmentation.md) - 5-tier network isolation
- [TensorZero Migration](./TENSORZERO_MIGRATION.md) - Schema migration guide
- [Docker Compose Design](./DOCKER_COMPOSE_DESIGN.md) - Container orchestration patterns
