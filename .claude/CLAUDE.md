# PMOVES-BoTZ Developer Context

> **🗄️ Archived 2026-04-19.** PMOVES-BoTZ is no longer active in the production mesh.
>
> - **Successor:** the BoTZ "expanded senses" architecture (12 senses, signal/noise via CHIT contracts) lives in `pmoves/services/` plus the skills constellation under `skills/`. See parent memory `project_botz_glances_architecture.md`.
> - **Per-feature replacements:**
>   - Document processing → `pmoves/services/extract-worker/` + `pmoves/services/ffmpeg-whisper/`
>   - Memory/reasoning → `pmoves-cipher` (parent submodule), Cipher MCP SSE at `:8105`
>   - Vision/Language → `pmoves/services/vl-sentinel/` (when present)
>   - Workflow automation → n8n service in parent + `/n8n:*` skills
> - **When to read this file:** only if you're cleaning up a stale BoTZ reference, salvaging a useful artifact, or doing the BoTZ archive forensic (see parent `pmoves/docs/audit/`).
>
> Do not build new features against this codebase. Direct new work to the parent `pmoves/services/` tree.

**Historical context follows.** Always-on context for Claude Code CLI when working in the PMOVES-BoTZ repository.

## Architecture Overview

PMOVES-BoTZ is a **unified multi-agent MCP platform** providing:
- Document processing and conversion (Docling)
- Memory management and reasoning (Cipher/PsyFeR-Holo)
- Secure code execution (E2B sandbox)
- Vision-language processing (VL Sentinel)
- API testing automation (Postman)
- Workflow automation (n8n integration)
- Security hooks for agent safety (patterns.yaml + hooks/)

## Security Hooks

Agent safety is enforced via `patterns.yaml` and the `hooks/` directory:

| File | Purpose |
|------|---------|
| `patterns.yaml` | Security constitution with deterministic rules and path protection |
| `hooks/pre_command.py` | Pre-execution validation for Bash/Edit/Write tools |
| `hooks/prompt_scan.py` | LLM-based prompt injection detection |
| `hooks/audit_log.py` | Post-execution logging to `memory/audit/` |

**Path Protection Tiers:**
- **Zero-access:** `.env*`, `*.pem`, `*.key`, `**/secrets/**` (no read/write)
- **Read-only:** `.git/`, `patterns.yaml`, `*.lock` (read allowed, no modify)
- **No-delete:** `core/**`, `features/**`, `docs/**` (modify allowed, no delete)

**Run tests:** `python hooks/test_hooks.py`

## Multi-Agent Orchestration

PMOVES-BoTZ uses mprocs for multi-agent orchestration (`.mprocs.yaml`):

```
                    ┌─────────────────┐
                    │   GATEWAY       │ (Entry Point)
                    │   Task Dispatch │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼───────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   ARCHITECT   │ │   BUILDER   │ │   AUDITOR   │
    │   (Opus 4.5)  │ │  (Sonnet)   │ │  (Haiku)    │
    │   Planning    │ │  Execution  │ │  Security   │
    └───────────────┘ └─────────────┘ └─────────────┘
```

**Start Orchestration:**
```bash
mprocs                                    # Standalone mode
mprocs --env PMOVES_DOCKED_MODE=true      # Docked mode
```

**Thread Types:**
| Type | Description |
|------|-------------|
| Base (B) | Single prompt-response |
| Parallel (P) | Multiple agents simultaneously |
| Chained (C) | Sequential dependencies |
| Fusion (F) | Multi-model consensus |
| Zero Touch (Z) | Fully autonomous |

**Memory & Expertise:**
- `memory/architecture.md` - System architecture
- `memory/status.md` - Current swarm state
- `memory/expertise/code_patterns.yaml` - Learned patterns
- `memory/expertise/security_patterns.yaml` - Security rules
- `memory/expertise/pmoves_integration.yaml` - Docked/Standalone patterns

## MCP Server Catalog

### Document Processing

**Docling MCP** [Port 3020]
- Document conversion (PDF, DOCX, HTML, images)
- Structured data extraction
- Transport: SSE at `http://localhost:3020/sse`
- **Use for:** PDF parsing, document conversion, table extraction

### Memory & Reasoning

**Cipher Memory** [Port 8081 / STDIO]
- Dual-layer memory system (System 1: concepts, System 2: reasoning)
- LLM-powered pattern recognition
- Transport: stdio via docker exec
- Config: `features/cipher/pmoves_cipher/memAgent/cipher_pmoves.yml`
- **Use for:** Persistent memory, learning patterns, context recall

### Code Execution

**E2B Sandbox** [Port 7071]
- Secure Python/JavaScript execution
- Isolated container environments
- Transport: SSE at `http://localhost:7071/sse`
- Requires: `E2B_API_KEY`
- **Use for:** Code testing, sandboxed execution, dynamic code generation

### Vision-Language

**VL Sentinel** [Port 7072]
- Image analysis and understanding
- Visual grounding and OCR
- Transport: SSE at `http://localhost:7072/sse`
- Backend: Ollama (requires `host.docker.internal:11434`)
- **Use for:** Image analysis, visual reasoning, screenshot understanding

### API Testing

**Postman MCP** [STDIO]
- API collection management
- Request execution and testing
- Transport: stdio via docker exec
- Requires: `POSTMAN_API_KEY`
- **Use for:** API testing, collection management, request automation

### Workflow Automation

**n8n Agent** [STDIO]
- Workflow creation and execution
- TensorZero-backed AI suggestions
- Transport: stdio via docker exec
- Config: `N8N_API_KEY`, `N8N_API_URL`
- **Use for:** Workflow automation, process orchestration

### Infrastructure Management

**Hostinger MCP** [STDIO]
- VPS, DNS, and domain management
- Requires: `HOSTINGER_API_KEY`

## Feature Modules (17 total)

| Module | Purpose |
|--------|---------|
| `cipher/` | Cipher Memory with PsyFeR-Holo integration |
| `docling/` | Document processing and conversion |
| `e2b/` | E2B sandbox execution |
| `vl_sentinel/` | Vision-language processing |
| `gateway/` | MCP Gateway aggregation |
| `n8n/` | n8n workflow integration + n8n-mcp knowledge base |
| `postman/` | API testing and collections |
| `hostinger/` | Hosting infrastructure management |
| `metrics/` | Prometheus metrics collection |
| `network/` | Network utilities and diagnostics |
| `discord/` | Discord bot integration |
| `slack/` | Slack integration |
| `yt/` | YouTube mini agent |
| `mini/` | Lightweight agent variants |
| `pro/` | Pro-tier features |
| `pro-plus/` | Pro-plus tier features |
| `crush/` | PMOVES-Crush CLI integration |

## Quick Start Commands

### Start All Services
```bash
cd PMOVES-BoTZ
./scripts/start.ps1  # Windows
# or
docker compose -f core/docker-compose/docker-compose.yml up -d
```

### Check Service Health
```bash
curl http://localhost:3020/health   # Docling
curl http://localhost:7071/health   # E2B
curl http://localhost:7072/health   # VL Sentinel
```

### Use Cipher Memory
```bash
# Store a memory
docker exec -i pmz-cipher python3 memory_shim/app_cipher_memory.py << 'EOF'
{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "store_memory", "arguments": {"key": "test", "content": "Test content"}}, "id": 1}
EOF

# Recall a memory
docker exec -i pmz-cipher python3 memory_shim/app_cipher_memory.py << 'EOF'
{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "recall_memory", "arguments": {"query": "test"}}, "id": 2}
EOF
```

## Deployment Modes

PMOVES-BoTZ supports two deployment modes:

### Standalone Mode (Default)
```bash
# Start with local services
docker compose -f core/docker-compose/base.yml -f core/docker-compose/overlays/development.yml up -d
```
- Uses local Ollama for LLM inference
- Cipher Memory for knowledge storage
- No external dependencies
- Networks: `172.31.x.0/24` (internal)

### Docked Mode (PMOVES.AI Integration)
```bash
# Start connected to parent cluster
docker compose -f core/docker-compose/base.yml -f core/docker-compose/overlays/docked.yml up -d
```
- Connects to parent PMOVES.AI services
- Uses TensorZero for LLM routing
- Publishes events to NATS
- Networks: `172.30.x.0/24` (external)

**Mode Detection:** Set `PMOVES_DOCKED_MODE=true` environment variable

**Reference:** `memory/expertise/pmoves_integration.yaml`

## Integration with PMOVES.AI

### Parent Repository
- **Repo:** https://github.com/POWERFULMOVES/PMOVES.AI
- **Production Branch:** `PMOVES.AI-Edition-Hardened`

### Parent Repository Services
BoTZ integrates with PMOVES.AI production services:

| Service | Port | Use For |
|---------|------|---------|
| TensorZero | 3000 | LLM calls, embeddings |
| Hi-RAG v2 | 8086 | Knowledge retrieval |
| NATS | 4222 | Event coordination |
| Qdrant | 6333 | Vector storage |
| Meilisearch | 7700 | Full-text search |

### NATS Event Subjects
```
botz.mcp.tool.executed.v1      # MCP tool execution
botz.cipher.memory.stored.v1   # Memory stored
botz.cipher.memory.recalled.v1 # Memory recalled
botz.gateway.task.dispatched.v1 # Gateway task dispatch
botz.agent.thread.started.v1   # Agent thread lifecycle
```

## Adding New Features

### Feature Structure
```
features/{feature-name}/
├── app_{feature}.py          # MCP server implementation
├── Dockerfile                # Container definition
├── requirements.txt          # Python dependencies
└── README.md                 # Feature documentation
```

### Register in Catalog
Add to `core/mcp/catalog.yml`:
```yaml
{feature-name}:
  url: http://localhost:{port}/sse  # or command: docker exec
  transport: sse                    # or stdio
```

## Development Patterns

### MCP Tool Implementation
```python
from mcp import Tool
from mcp.server import Server

server = Server("my-feature")

@server.list_tools()
async def list_tools():
    return [Tool(name="my_tool", description="...", inputSchema={...})]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "my_tool":
        # Implementation
        return CallToolResult(content=[TextContent(type="text", text="result")])
```

### Docker Compose Pattern
```yaml
services:
  my-feature:
    build: ./features/my-feature
    ports:
      - "7073:7073"
    environment:
      - API_KEY=${MY_API_KEY}
```

## Configuration

### Environment Variables
```bash
# Required for services
E2B_API_KEY=...           # E2B sandbox
POSTMAN_API_KEY=...       # Postman collections
HOSTINGER_API_KEY=...     # Hostinger VPS
N8N_API_KEY=...           # n8n workflows
VENICE_API_KEY=...        # Cipher memory LLM

# TensorZero integration
TENSORZERO_BASE_URL=http://tensorzero:3000

# Ollama for VL Sentinel
OLLAMA_HOST=http://host.docker.internal:11434
```

### Linux Host Configuration
For `host.docker.internal` support:
```bash
docker run --add-host=host.docker.internal:host-gateway ...
```

## Testing

```bash
# Run all tests
./scripts/test.ps1

# Test specific feature
pytest features/cipher/tests/
pytest features/docling/tests/
```

## TAC Commands Available

| Command | Description |
|---------|-------------|
| `/botz:start` | Start all BoTZ services |
| `/botz:status` | Check service health |
| `/botz:mcp-catalog` | View MCP server catalog |
| `/cipher:store` | Store memory item |
| `/cipher:recall` | Recall memory by query |
| `/cipher:status` | Check Cipher health |

## Meta-Instructions

When developing for PMOVES-BoTZ:
1. **Use existing MCP servers** - Don't rebuild capabilities
2. **Follow catalog pattern** - Register in `catalog.yml`
3. **Expose health endpoints** - `/health` or `/healthz`
4. **Use TensorZero** - For LLM calls and embeddings
5. **Publish to NATS** - For event coordination
6. **Leverage Cipher** - For persistent memory across sessions

BoTZ extends PMOVES.AI with specialized MCP tooling. Your role is to build features that integrate with this ecosystem.
