# PMOVES Cipher Memory Integration Guide

## Overview

PMOVES-BoTZ now includes robust integration with Pmoves-cipher, providing advanced memory capabilities for multi-agent workflows. This integration enables persistent knowledge storage, reasoning pattern preservation, and cross-session learning.

## Architecture

### Components

1. **Pmoves-cipher Submodule**
   - Location: `pmoves_multi_agent_pro_pack/memory_shim/pmoves_cipher/`
   - Forked from: https://github.com/POWERFULMOVES/Pmoves-cipher
   - Provides core memory management and vector storage capabilities

2. **Cipher Memory MCP Server**
   - Script: `pmoves_multi_agent_pro_pack/memory_shim/app_cipher_memory.py`
   - Interfaces between PMOVES MCP architecture and cipher memory system
   - Exposes memory operations as MCP tools

3. **Enhanced Modes**
   - `cipher_memory_mode.json`: Dedicated memory management mode
   - Enhanced `auto_research_mode.json`: Memory-augmented research
   - Enhanced `code_runner_mode.json`: Learning from code execution

4. **Docker Integration**
   - Service: `cipher-memory` in `docker-compose.mcp-pro.yml`
   - Uses custom Dockerfile: `Dockerfile.cipher`
   - Persistent storage via Docker volume

## Setup Instructions

### Prerequisites

1. **Git Submodule Initialization**
   ```bash
   git submodule update --init --recursive
   ```

2. **Node.js and pnpm**
   ```bash
   # Install Node.js (v20+)
   # Install pnpm globally
   npm install -g pnpm
   ```

3. **Venice AI API Key**
   - Required for cipher embeddings and LLM operations
   - Set in environment: `VENICE_API_KEY=your-venice-key`

### Automated Setup

#### Linux/macOS
```bash
cd pmoves_multi_agent_pro_pack/memory_shim
chmod +x setup_cipher.sh
./setup_cipher.sh
```

#### Windows
```powershell
cd pmoves_multi_agent_pro_pack\memory_shim
.\setup_cipher.ps1
```

### Manual Setup

1. **Build Cipher**
   ```bash
   cd pmoves_multi_agent_pro_pack/memory_shim/pmoves_cipher
   pnpm install --frozen-lockfile
   pnpm run build:no-ui
   ```

2. **Configure Environment**
   ```bash
   # Required
   export VENICE_API_KEY=your-venice-key
   
   # Optional
   export CIPHER_CONFIG_PATH=memory_shim/pmoves_cipher/memAgent/cipher_pmoves.yml
   export PMOVES_ROOT=/path/to/pmoves
   ```

## Usage

### Memory Operations

#### Storing Knowledge
```json
{
  "tool": "cipher_store_memory",
  "arguments": {
    "content": "API authentication requires Bearer token format",
    "memory_type": "knowledge",
    "session_id": "api_integration_session"
  }
}
```

#### Searching Memory
```json
{
  "tool": "cipher_search_memory",
  "arguments": {
    "query": "API authentication patterns",
    "limit": 10
  }
}
```

#### Storing Reasoning
```json
{
  "tool": "cipher_store_reasoning_memory",
  "arguments": {
    "reasoning": "Step 1: Validate token format, Step 2: Check expiration, Step 3: Verify permissions",
    "context": "JWT token validation for API access"
  }
}
```

### Mode Integration

#### Cipher Memory Mode
- **Purpose**: Dedicated memory management operations
- **Tools**: All cipher-memory:* tools
- **Use Cases**: Knowledge base management, pattern extraction, reasoning storage

#### Enhanced Auto Research Mode
- **New Capabilities**: Memory-augmented research
- **Workflow**: Search memory → Analyze docs → Execute code → Store findings
- **Benefits**: Leverages past research, avoids duplication, builds knowledge base

#### Enhanced Code Runner Mode
- **New Capabilities**: Learning from code execution
- **Workflow**: Search patterns → Execute → Store results → Document issues
- **Benefits**: Code pattern reuse, error resolution knowledge, performance optimization

## Workflow Templates

### Memory-Driven Research
1. Search cipher memory for relevant past research
2. Extract new information using Docling
3. Execute code in E2B sandbox
4. Validate with VL Sentinel
5. Store findings and reasoning patterns

### Adaptive Code Generation
1. Search memory for similar coding problems
2. Implement based on learned patterns
3. Test and validate in sandbox
4. Store successful patterns and solutions

### Multi-Agent Coordination
1. Establish shared memory session
2. Load relevant historical context
3. Coordinate specialized agent work
4. Store collaboration patterns

## Configuration

### Cipher Configuration
Located at: `memory_shim/pmoves_cipher/memAgent/cipher_pmoves.yml`

```yaml
llm:
  provider: openai
  model: llama-3.2-3b-instruct
  apiKey: $VENICE_API_KEY
  baseURL: https://api.venice.ai/api/v1

embedding:
  provider: openai
  model: text-embedding-3-small
  apiKey: $VENICE_API_KEY
  baseURL: https://api.venice.ai/api/v1

systemPrompt:
  enabled: true
  content: |
    You are an AI memory assistant for PMOVES multi-agent workflows.
    Your role is to manage persistent knowledge, reasoning patterns, and cross-session learning.
    Always provide accurate, contextual responses based on stored memories and current context.
```

### MCP Catalog Integration
Updated in: `pmoves_multi_agent_pro_pack/mcp_catalog_multi.yaml`

```yaml
servers:
  cipher-memory:
    type: stdio
    command: python3
    args: ["memory_shim/app_cipher_memory.py"]
    env:
      VENICE_API_KEY: "${VENICE_API_KEY}"
      CIPHER_CONFIG_PATH: "memory_shim/pmoves_cipher/memAgent/cipher_pmoves.yml"
```

## Docker Deployment

### Service Configuration
```yaml
cipher-memory:
  build:
    context: ./memory_shim
    dockerfile: Dockerfile.cipher
  environment:
    VENICE_API_KEY: ${VENICE_API_KEY}
    CIPHER_CONFIG_PATH: /app/memory_shim/pmoves_cipher/memAgent/cipher_pmoves.yml
  volumes:
    - ./memory_shim/pmoves_cipher:/app/memory_shim/pmoves_cipher:ro
    - cipher_data:/data
  network_mode: host
```

### Volume Management
- `cipher_data`: Persistent storage for memory database
- Read-only mount: Cipher binary and configuration
- Host networking: For MCP communication

## Testing

### Smoke Tests
Enhanced smoke tests now include cipher memory validation:

```bash
python scripts/smoke_tests.py
```

**Test Categories:**
- Cipher Submodule: Verifies git submodule is initialized
- Cipher Build: Confirms cipher is compiled
- OpenAI API: Validates API key format
- Cipher Config: Checks PMOVES configuration exists
- Memory Server: Verifies MCP server script

### Manual Testing

1. **Memory Storage Test**
   ```bash
   # Start cipher memory server
   python3 pmoves_multi_agent_pro_pack/memory_shim/app_cipher_memory.py
   
   # Test with MCP client
   ```

2. **Integration Test**
   ```bash
   # Start full pro stack
   docker-compose -f pmoves_multi_agent_pro_pack/docker-compose.mcp-pro.yml up -d
   
   # Test memory operations through MCP gateway
   ```

## Troubleshooting

### Common Issues

#### Submodule Not Found
```
Error: Cipher Submodule: Not found - run git submodule update --init
```
**Solution**: Initialize git submodules
```bash
git submodule update --init --recursive
```

#### Cipher Not Built
```
Error: Cipher Build: Cipher not built - run setup script
```
**Solution**: Run setup script or build manually
```bash
cd pmoves_multi_agent_pro_pack/memory_shim
./setup_cipher.sh  # Linux/macOS
# or
.\setup_cipher.ps1  # Windows
```

#### Venice AI API Key Issues
```
Error: Venice AI API: Missing or invalid Venice AI API key for cipher
```
**Solution**: Set valid Venice AI API key
```bash
export VENICE_API_KEY=your-valid-venice-key
```

#### Memory Server Connection
```
Error: Failed to connect to cipher memory server
```
**Solution**: Check Docker logs and environment
```bash
docker-compose logs cipher-memory
```

### Debug Mode

Enable verbose logging:
```bash
export CIPHER_LOG_LEVEL=debug
export PYTHONUNBUFFERED=1
```

## Performance Considerations

### Memory Usage
- Monitor database size in `cipher_data` volume
- Implement cleanup routines for old memories
- Use memory type categorization for efficient retrieval

### API Rate Limits
- Venice AI API has rate limits for embeddings
- Implement caching for frequently accessed memories
- Use batch operations when possible

### Storage Optimization
- Vector embeddings can be storage-intensive
- Consider compression for long-term storage
- Regular maintenance of vector indices

## Advanced Features

### Custom Memory Types
Define specialized memory types for different use cases:
- `code_pattern`: Reusable code solutions
- `error_resolution`: Troubleshooting strategies
- `api_pattern`: API integration patterns
- `workflow_template`: Process definitions

### Session Management
Create dedicated sessions for different contexts:
- Project-specific sessions
- Agent-type sessions
- Temporal sessions (daily/weekly)

### Knowledge Graph Integration
Leverage cipher's knowledge graph capabilities:
- Entity relationship mapping
- Concept hierarchies
- Cross-domain knowledge connections

## Security Considerations

### Data Privacy
- Filter sensitive information before storage
- Implement access controls for shared memories
- Regular security audits of stored data

### API Security
- Secure storage of API keys
- Use environment variables for credentials
- Rotate API keys regularly

### Network Security
- Cipher memory server runs on host network
- Ensure proper firewall configuration
- Monitor for unauthorized access attempts

## Future Enhancements

### Planned Features
1. **Multi-Modal Memory**: Support for images, audio, video
2. **Distributed Memory**: Multi-node memory clusters
3. **Real-time Sync**: Live memory synchronization
4. **Advanced Analytics**: Memory usage patterns and insights
5. **Custom Embeddings**: Support for local embedding models

### Integration Roadmap
1. **Enhanced UI**: Web interface for memory management
2. **API Gateway**: RESTful API for external integrations
3. **Plugin System**: Extensible memory providers
4. **Performance Monitoring**: Metrics and alerting
5. **Backup/Restore**: Memory export/import capabilities

## Support

### Documentation
- [Pmoves-cipher Documentation](https://github.com/POWERFULMOVES/Pmoves-cipher)
- [PMOVES Documentation](./README.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

### Community
- Issues: [GitHub Issues](https://github.com/POWERFULMOVES/PMOVES-Kilobots/issues)
- Discussions: [GitHub Discussions](https://github.com/POWERFULMOVES/PMOVES-Kilobots/discussions)

### Contributing
- Fork the repository
- Create feature branches
- Submit pull requests
- Follow contribution guidelines

This integration significantly enhances PMOVES-BoTZ with persistent memory capabilities, enabling more sophisticated multi-agent workflows that learn and improve over time.