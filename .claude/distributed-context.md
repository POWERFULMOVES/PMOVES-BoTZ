# BoTZ Distributed Deployment Context

> Context file for Claude Code when working with BoTZ in distributed mode.

## Architecture Position

BoTZ is the **Agent Platform** module in the PMOVES ecosystem. It hosts:

- **MCP Gateway** (:2091): Unified tool access point
- **Archon**: Knowledge backbone + Agent Forge
- **Cipher Memory** (:8081): Persistent memory system
- **Skills Catalog**: Multi-layer agent orchestration

```
┌─────────────────────────────────────────────┐
│                   BoTZ                       │
│  ┌──────────────┐  ┌──────────────┐         │
│  │    Archon    │  │ MCP Gateway  │         │
│  │ (Knowledge + │  │    :2091     │         │
│  │ Agent Forge) │  │              │         │
│  └──────────────┘  └──────────────┘         │
│                                              │
│  ┌──────────────┐  ┌──────────────┐         │
│  │Cipher Memory │  │   Skills     │         │
│  │    :8081     │  │  Catalog     │         │
│  └──────────────┘  └──────────────┘         │
│                                              │
│  Multi-layer Orchestration (P/C/F threads)  │
└──────────────────────────────────────────────┘
```

## Service Discovery

### Environment Variables (Distributed Mode)

```bash
# This service
BOTZ_HOST=192.168.1.30
BOTZ_GATEWAY_PORT=2091
BOTZ_GATEWAY_URL=http://${BOTZ_HOST}:${BOTZ_GATEWAY_PORT}

# Parent services
NATS_URL=nats://192.168.1.10:4222
TENSORZERO_URL=http://192.168.1.10:3030
SUPABASE_URL=http://192.168.1.10:54321

# Sibling submodules
DOX_BACKEND_URL=http://192.168.1.20:8484
TOKENISM_URL=http://192.168.1.40:5000
```

### Configuration Files

| File | Purpose |
|------|---------|
| `env.distributed.example` | Template for cross-host configuration |
| `docker-compose.distributed.yml` | Overlay for distributed networks |
| `core/mcp/catalog.yml` | MCP server registry |

## MCP Gateway Architecture

### JWT Authentication

All distributed MCP calls require JWT authentication:

```bash
SUPABASE_JWT_SECRET=your-shared-secret
```

Header format:
```
Authorization: Bearer <jwt-token>
```

### Gateway Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Gateway health status |
| `/healthz` | GET | Standard health check |
| `/metrics` | GET | Prometheus metrics |
| `/servers` | GET | List upstream MCP servers (auth required) |
| `/tools` | GET | List available MCP tools (auth required) |
| `/tools/{server}` | GET | List tools from specific server (auth required) |
| `/call` | POST | Invoke MCP tool (auth required) |
| `/mcp` | POST | MCP JSON-RPC endpoint (auth required) |
| `/.well-known/agent.json` | GET | A2A agent card (auth required) |
| `/a2a/v1/tasks` | POST | A2A task lifecycle (auth required) |

## NATS Subjects (Published)

BoTZ publishes to these NATS subjects:

| Subject | Description |
|---------|-------------|
| `botz.mcp.tool.executed.v1` | MCP tool execution complete |
| `botz.cipher.memory.stored.v1` | Memory stored |
| `botz.cipher.memory.recalled.v1` | Memory recalled |
| `botz.gateway.task.dispatched.v1` | Task dispatched |
| `botz.agent.thread.started.v1` | Agent thread lifecycle |
| `botz.archon.knowledge.updated.v1` | Knowledge graph update |

## NATS Subjects (Subscribed)

BoTZ subscribes to:

| Subject | Source | Description |
|---------|--------|-------------|
| `dox.document.ingested.v1` | DoX | Document ready for processing |
| `tokenism.simulation.complete.v1` | Tokenism | Simulation results |

## Archon Integration

Archon provides:

1. **Knowledge Graph**: Neo4j-backed semantic storage
2. **Agent Forge**: Dynamic agent creation
3. **Skill Taxonomy**: Hierarchical skill organization

### Knowledge Query

```python
# Via MCP Gateway
POST /call
{
  "tool": "archon_query",
  "arguments": {
    "query": "MATCH (n:Concept) RETURN n LIMIT 10"
  }
}
```

## Cipher Memory

Dual-layer memory system:

- **System 1**: Fast concept lookup (Redis-backed)
- **System 2**: Deep reasoning traces (Neo4j-backed)

### Memory Operations

```python
# Store memory
POST /call
{
  "tool": "store_memory",
  "arguments": {"key": "project_context", "content": "..."}
}

# Recall memory
POST /call
{
  "tool": "recall_memory",
  "arguments": {"query": "project context"}
}
```

## DoX Discovery

BoTZ discovers DoX via agent-card:

```bash
curl http://${DOX_HOST}:8484/.well-known/agent-card
```

### A2A Protocol

BoTZ can dispatch tasks to DoX:

```python
POST http://${DOX_HOST}:8484/orchestrate/dispatch
{
  "task": "process_document",
  "payload": {"document_id": "..."}
}
```

## Multi-Agent Orchestration

### Thread Types

| Type | Symbol | Description |
|------|--------|-------------|
| Parallel | P | Multiple agents simultaneously |
| Chained | C | Sequential dependencies |
| Fusion | F | Multi-model consensus |
| Zero-Touch | Z | Fully autonomous |

### mprocs Orchestration

```bash
# Start multi-agent swarm
mprocs

# Docked mode (parent integration)
mprocs --env PMOVES_DOCKED_MODE=true
```

## Skills Catalog

Skills are registered in `core/mcp/catalog.yml`:

```yaml
docling:
  url: http://localhost:3020/sse
  transport: sse
  capabilities: [document_conversion, table_extraction]

cipher:
  command: docker exec -i pmz-cipher python3 memory_shim/app_cipher_memory.py
  transport: stdio
  capabilities: [memory_store, memory_recall]
```

## Troubleshooting

### Gateway JWT Rejected

1. Verify SUPABASE_JWT_SECRET matches parent
2. Check token expiration
3. Ensure Authorization header format

### Archon Connection Failed

1. Verify Neo4j credentials
2. Check network connectivity to Neo4j host
3. Review Archon container logs

### Cipher Memory Timeout

1. Check Redis connectivity
2. Verify Venice API key for LLM operations
3. Review Cipher container health

## Related Documentation

- [PMOVES.AI DISTRIBUTED_SUBMODULES.md](../../pmoves/docs/DISTRIBUTED_SUBMODULES.md)
- [BoTZ CLAUDE.md](../CLAUDE.md)
- [MCP Gateway README](../features/gateway/README.md)
