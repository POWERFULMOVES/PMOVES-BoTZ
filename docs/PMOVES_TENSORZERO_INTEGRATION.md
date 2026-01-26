# PMOVES-TensorZero Integration Patterns

**Status:** Tracking PMOVES-tensorzero PR #1 (not yet merged)
**Last Updated:** 2026-01-26

This document describes integration patterns from PMOVES-tensorzero that should be adopted by PMOVES-BoTZ.

---

## 1. CHIT Secrets Management

CHIT (Compressed Hierarchical Injected Tokens) provides centralized secrets management.

### Configuration File

Location: `chit/secrets_manifest_v2.yaml`

### Precedence Order

| Source | Precedence | Description |
|--------|------------|-------------|
| Environment Variables | 50 | Static overrides from `.env` or container env |
| CHIT Vault | 100 | Runtime secrets from centralized vault |

Higher precedence values override lower ones.

---

## 2. Tier-Based Environment Loading

PMOVES uses a tiered environment configuration system.

### File Structure

```
project-root/
  env.shared           # Base PMOVES.AI service configuration
  env.tier-agent       # Agent tier (dotenv format for Docker Compose)
  env.tier-agent.sh    # Agent tier (shell format with exports)
  env.tier-llm.sh      # LLM tier specific variables
```

### Docker Compose YAML Anchors

```yaml
x-env-shared: &env-shared
  PMOVES_ENV: ${PMOVES_ENV:-production}
  NATS_URL: ${NATS_URL:-nats://nats:4222}

x-env-agent: &env-agent
  <<: *env-shared
  TIER: agent
  MAX_CONCURRENT_AGENTS: ${MAX_CONCURRENT_AGENTS:-50}

services:
  my-service:
    environment:
      <<: *env-agent
      SERVICE_NAME: my-service
```

---

## 3. Service Discovery

### Fallback Chain

1. **Environment Variables** - Static overrides (highest priority)
2. **Supabase** - Dynamic service catalog
3. **NATS Announcements** - Real-time service discovery
4. **Docker DNS** - Development fallback (lowest priority)

### Service Announcer

Location: `pmoves_announcer/`

NATS Subject: `services.announce.v1`

```python
from pmoves_announcer import announce_service

await announce_service(
    slug="my-service",
    url="http://my-service:8080",
    tier="api"
)
```

### Service Registry

Location: `pmoves_registry/`

```python
from pmoves_registry import get_service_url

url = await get_service_url("hirag-v2")
# Returns: http://hi-rag-gateway-v2:8086
```

---

## 4. Health Endpoints

Location: `pmoves_health/`

### Standard Endpoint

All services expose `/healthz`:

```python
from fastapi import FastAPI
from pmoves_health import health_check_router

app = FastAPI()
app.include_router(health_check_router)
```

### Response Format

```json
{
  "status": "healthy",
  "service": "my-service",
  "timestamp": "2026-01-26T12:00:00Z"
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

**URL:** https://github.com/POWERFULMOVES/PMOVES-tensorzero/pull/1
**Status:** Open (not yet merged)

### Components from PR #1

| Component | File(s) | Description |
|-----------|---------|-------------|
| CHIT Secrets | `chit/secrets_manifest_v2.yaml` | Compressed secrets handling |
| Tier Env | `env.shared`, `env.tier-llm.sh` | Environment loading |
| Announcer | `pmoves_announcer/__init__.py` | NATS service announcements |
| Registry | `pmoves_registry/__init__.py` | Service URL resolution |
| Health | `pmoves_health/__init__.py` | Health check endpoints |
| Docs | `PMOVES.AI_INTEGRATION.md` | Integration guide |
| Compose | `docker-compose.pmoves.yml` | YAML anchor patterns |

### Action Items

1. **Track PR #1** - Monitor for merge status
2. **Sync Updates** - After merge, verify BoTZ modules match upstream
3. **Add Supabase Backend** - Implement service catalog lookup
4. **Add NATS Cache** - Implement announcement caching

---

## Related Documentation

- [Architecture Overview](./ARCHITECTURE_BOTZ.md)
- [Network Tier Segmentation](./network-tier-segmentation.md)
- [Docker Compose Design](./DOCKER_COMPOSE_DESIGN.md)
- [TensorZero Migration](./TENSORZERO_MIGRATION.md)
