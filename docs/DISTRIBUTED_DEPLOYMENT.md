# PMOVES-BoTZ Distributed Deployment Guide

This guide explains how to deploy PMOVES-BoTZ on separate hardware from other PMOVES submodules while maintaining connectivity via local network, Tailscale, or VPS.

## Overview

BoTZ (Multi-Agent MCP Platform) can run independently on any host with:
- Docker and Docker Compose v2
- Network connectivity to other PMOVES services
- GPU recommended for vision-language and local LLM inference

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/POWERFULMOVES/PMOVES-BoTZ.git
cd PMOVES-BoTZ

# Copy distributed configuration template
cp env.distributed.example .env

# Edit for your network topology
nano .env
```

### 2. Start BoTZ

```bash
# With distributed overlay
docker compose -f docker-compose.yml -f docker-compose.distributed.yml up -d

# With optional profiles (cipher, tools, e2b, ollama)
docker compose -f docker-compose.yml -f docker-compose.distributed.yml \
  --profile cipher --profile tools up -d

# Check status
docker compose ps
curl http://localhost:2091/health
```

## Configuration

### Required Environment Variables

```bash
# Network Mode
DEPLOYMENT_MODE=distributed
DOCKED_MODE=false
STANDALONE_NETWORK=true

# Authentication (required for distributed)
SUPABASE_JWT_SECRET=your-secure-jwt-secret

# This service (BoTZ Gateway)
GATEWAY_PORT=2091
MCP_BRIDGE_PORT=8100
```

### Service Discovery

```bash
# TensorZero LLM Gateway (required for LLM operations)
TENSORZERO_HOST=192.168.1.10
TENSORZERO_URL=http://${TENSORZERO_HOST}:3030

# DoX Document Intelligence
DOX_HOST=192.168.1.20
DOX_BACKEND_URL=http://${DOX_HOST}:8484

# Tokenism
TOKENISM_HOST=192.168.1.30
TOKENISM_URL=http://${TOKENISM_HOST}:5000

# NATS Message Bus
NATS_HOST=192.168.1.10
NATS_URL=nats://${NATS_HOST}:4222
```

## Network Topologies

### Local Network (192.168.x.x)

For AI Lab setups where all machines are on the same LAN:

```bash
# .env
TENSORZERO_HOST=192.168.1.10
DOX_HOST=192.168.1.20
BOTZ_HOST=192.168.1.30
NATS_HOST=192.168.1.10
```

### Tailscale Mesh (100.x.x.x)

For geographically distributed hosts:

```bash
# .env
TENSORZERO_HOST=100.64.1.10
DOX_HOST=100.64.1.20
NATS_HOST=100.64.1.10

# Enable Tailscale sidecar
TAILSCALE_ENABLED=true
TAILSCALE_AUTHKEY=tskey-auth-xxxxx
TAILSCALE_HOSTNAME=pmoves-botz
```

Start with Tailscale profile:

```bash
docker compose -f docker-compose.yml -f docker-compose.distributed.yml \
  --profile tailscale up -d
```

### VPS Deployment

For deploying BoTZ Gateway on a Hostinger KVM:

```bash
# .env
TENSORZERO_HOST=your-vps.example.com
DOX_HOST=your-dox-vps.example.com

# Expose on all interfaces
HOST=0.0.0.0
```

## Authentication

### JWT Validation

The MCP Gateway validates JWT tokens for protected endpoints:

**Protected Endpoints:**
- `POST /call` - Tool execution
- `POST /mcp` - MCP JSON-RPC
- `GET /tools/*` - Tool management
- `GET /servers/*` - Server management

**Public Endpoints:**
- `GET /health` - Health check
- `GET /healthz` - Kubernetes-style health
- `GET /metrics` - Prometheus metrics
- `GET /.well-known/agent.json` - A2A manifest

### Making Authenticated Requests

```bash
# Using Authorization header
curl -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:2091/tools

# Using query parameter
curl "http://localhost:2091/tools?token=$JWT_TOKEN"
```

### Generating JWT Tokens

```python
import jwt

token = jwt.encode(
    {"sub": "user_id", "exp": datetime.utcnow() + timedelta(hours=1)},
    SUPABASE_JWT_SECRET,
    algorithm="HS256"
)
```

## Port Configuration

| Port | Service | Description |
|------|---------|-------------|
| 2091 | MCP Gateway | Main API gateway |
| 8100 | MCP Bridge | Internal bridge service |
| 3020 | Docling MCP | Document processing |
| 7071 | E2B Sandbox | Code execution |
| 7072 | VL Sentinel | Vision-language |
| 8081 | Cipher Memory | Memory service |
| 9091 | Metrics | Prometheus metrics |
| 11434 | Ollama | Local LLM |

## Service Profiles

BoTZ uses Docker Compose profiles to enable optional services:

| Profile | Services | Use Case |
|---------|----------|----------|
| `cipher` | cipher-memory | Persistent memory |
| `tools` | docling-mcp, vl-sentinel, metrics-collector | Document processing, vision |
| `e2b` | e2b-runner | Sandboxed code execution |
| `ollama` | ollama | Local LLM inference |

### Example Combinations

```bash
# Minimal (Gateway + Bridge only)
docker compose -f docker-compose.yml -f docker-compose.distributed.yml up -d

# With Cipher Memory
docker compose ... --profile cipher up -d

# Full stack
docker compose ... --profile cipher --profile tools --profile e2b --profile ollama up -d
```

## Health Checks

### Gateway Health

```bash
curl http://localhost:2091/health
# {"status": "healthy", "services": {...}}
```

### MCP Bridge Health

```bash
curl http://localhost:8100/healthz
# ok
```

### Cross-Service Connectivity

```bash
# Test BoTZ → TensorZero
curl http://${TENSORZERO_HOST}:3030/health

# Test BoTZ → DoX
curl http://${DOX_HOST}:8484/healthz

# Test BoTZ → NATS
curl http://${NATS_HOST}:8222/healthz
```

## Tool Execution

### Via MCP JSON-RPC

```bash
curl -X POST http://localhost:2091/mcp \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "docling.convert",
      "arguments": {"url": "https://example.com/doc.pdf"}
    },
    "id": 1
  }'
```

### Via /call Endpoint

```bash
curl -X POST http://localhost:2091/call \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server": "docling-mcp",
    "tool": "convert",
    "args": {"url": "https://example.com/doc.pdf"}
  }'
```

## GPU Configuration

### NVIDIA GPU

The distributed overlay works with the base GPU settings:

```bash
# Check GPU availability
docker exec pmoves-botz-gateway nvidia-smi
```

### CPU-Only Mode

For VPS deployments without GPU, services automatically fall back to CPU.

### Remote Ollama

Instead of running local Ollama, point to a remote instance:

```bash
OLLAMA_HOST=192.168.1.50
OLLAMA_BASE_URL=http://${OLLAMA_HOST}:11434
```

## Troubleshooting

### Authentication Errors

```
{"error": "Unauthorized", "detail": "NO_AUTH_PROVIDED"}
```

**Solutions:**
1. Include JWT token in Authorization header
2. Verify SUPABASE_JWT_SECRET matches token signing key
3. Check token expiration

### Connection Refused

```
Error: connect ECONNREFUSED 192.168.1.10:3030
```

**Solutions:**
1. Verify target service is running
2. Check firewall rules
3. Ensure service is listening on 0.0.0.0

### Tool Execution Failed

```
{"error": "Tool not found"}
```

**Solutions:**
1. Verify service profile is enabled
2. Check service health
3. Ensure tool is registered in catalog

### Network Isolation Issues

```
Error: could not resolve host
```

**Solutions:**
1. Use `docker-compose.distributed.yml` overlay
2. Check network mode is not "internal"
3. Verify STANDALONE_NETWORK=true

## Integration with Other Submodules

### DoX Integration

BoTZ can call DoX for document processing:

```bash
# In BoTZ environment
DOX_BACKEND_URL=http://${DOX_HOST}:8484
```

### Tokenism Integration

BoTZ communicates with Tokenism via NATS:

```bash
# NATS subjects
botz.mcp.tool.executed.v1
botz.gateway.task.dispatched.v1
```

## File Reference

| File | Purpose |
|------|---------|
| `env.distributed.example` | Environment template |
| `docker-compose.distributed.yml` | Distributed overlay |
| `.mprocs.yaml` | Multi-agent orchestration |
| `features/gateway/python-gateway/gateway.py` | MCP Gateway |
| `features/mcp_bridge/auth.py` | JWT authentication |
| `patterns.yaml` | Security patterns |

## Related Documentation

- [Parent PMOVES.AI Distributed Guide](../../pmoves/docs/DISTRIBUTED_SUBMODULES.md)
- [BoTZ CLAUDE.md](./.claude/CLAUDE.md)
- [MCP Bridge Auth](../features/mcp_bridge/auth.py)
