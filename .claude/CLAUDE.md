# PMOVES-BoTZ Developer Context

**Always-on context for Claude Code CLI when working in the PMOVES-BoTZ repository.**

## Architecture Overview

PMOVES-BoTZ is a **unified multi-agent MCP platform** providing:
- Document processing and conversion (Docling)
- Memory management and reasoning (Cipher/PsyFeR-Holo)
- Secure code execution (E2B sandbox)
- Vision-language processing (VL Sentinel)
- API testing automation (Postman)
- Workflow automation (n8n integration)

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

## Integration with PMOVES.AI

### Parent Repository Services
BoTZ integrates with PMOVES.AI production services:

| Service | Port | Use For |
|---------|------|---------|
| TensorZero | 3030 | LLM calls, embeddings |
| Hi-RAG v2 | 8086 | Knowledge retrieval |
| NATS | 4222 | Event coordination |
| Qdrant | 6333 | Vector storage |
| Meilisearch | 7700 | Full-text search |

### NATS Event Subjects
```
botz.mcp.tool.executed.v1     # MCP tool execution
botz.cipher.memory.stored.v1  # Memory stored
botz.cipher.memory.recalled.v1 # Memory recalled
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
