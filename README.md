# PMOVES-BoTZ

A collection of multi-agent packs for PMOVES (Portable Multi-Agent Orchestration and Validation Environment System).

## Agent Packs

### pmoves-mini-agent-box/
Portable MCP Gateway with Tailscale for remote access. Includes:
- MCP Gateway with portable catalog (Docling 1.3.1 via pipx)
- Tailscale for HTTPS exposure
- Crush shim for pmoves CLI execution
- Discord bot integration
- Slack app manifest and setup guide

### pmoves_multi_agent_pack/
Basic multi-agent pack with:
- Docker Compose for multi-agent setup
- MCP catalog for basic integrations
- Kilocode modes: docling, orchestrator, postman
- Templates for large projects and prompt engineering
- Workflows for docling-to-postman integration

### pmoves_multi_agent_pro_pack/
Professional multi-agent pack with:
- E2B shim for code execution
- VL Sentinel for vision/language processing
- **Pmoves-cipher memory integration for persistent knowledge and reasoning**
- Advanced kilocode modes including auto-research and code-runner
- N8N workflows for docling-postman-vl integration
- Memory-enhanced workflow templates and patterns

### pmoves_multi_agent_pro_plus_pack/
Enterprise multi-agent pack with:
- Local Postman integration
- VLM guard mode
- Automated OpenAPI to Postman collection generation
- Nightly regression testing via GitHub Actions
- CI/CD reporting to Slack

## Archive

Archived files from previous integrations are stored in the `archive/` directory.

## Getting Started

Each agent pack contains its own README and setup instructions. Choose the pack that matches your needs:

- **Mini**: Basic portable setup with Tailscale
- **Multi**: Standard multi-agent orchestration
- **Pro**: Advanced with code execution and vision
- **Pro Plus**: Enterprise with automated testing and local integrations

## Requirements

- Docker and Docker Compose
- Python 3.8+
- Node.js and pnpm (for cipher memory integration)
- OpenAI API key (for cipher embeddings and memory operations)
- Tailscale (for remote access in mini pack)

## New Features

### Cipher Memory Integration

PMOVES-BoTZ now includes advanced memory capabilities through Pmoves-cipher integration:

- **Persistent Knowledge Storage**: Store and retrieve coding patterns, solutions, and insights across sessions
- **Reasoning Pattern Preservation**: Capture and reuse decision-making processes and problem-solving approaches
- **Cross-Session Learning**: Agents improve over time through accumulated experience
- **Memory-Enhanced Modes**: Auto-research and code-runner modes now leverage persistent memory
- **Advanced Workflow Templates**: Memory-driven workflows for complex multi-agent coordination

### Quick Start with Cipher Memory

1. **Initialize Submodule**
   ```bash
   git submodule update --init --recursive
   ```

2. **Setup Cipher Memory**
   ```bash
   cd pmoves_multi_agent_pro_pack/memory_shim
   ./setup_cipher.sh  # Linux/macOS
   # or
   .\setup_cipher.ps1  # Windows
   ```

3. **Configure Environment**
   ```bash
   export OPENAI_API_KEY=sk-your-key
   ```

4. **Deploy with Memory**
   ```bash
   docker-compose -f pmoves_multi_agent_pro_pack/docker-compose.mcp-pro.yml up -d
   ```

For detailed setup instructions, see [Cipher Memory Integration Guide](docs/CIPHER_MEMORY_INTEGRATION.md).