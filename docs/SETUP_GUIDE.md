# PMOVES Agent Setup Guide

## Quick Start

Choose your configuration and get started in minutes:

### Basic Setup (Docling + Postman)
```bash
# Linux/macOS
./scripts/setup_pmoves.sh -c basic

# Windows PowerShell
.\scripts\setup_pmoves.ps1 -Config basic
```

### Pro Setup (Basic + E2B + VL Sentinel)
```bash
# Linux/macOS
./scripts/setup_pmoves.sh -c pro

# Windows PowerShell
.\scripts\setup_pmoves.ps1 -Config pro
```

### Full Setup (All Features)
```bash
# Linux/macOS
./scripts/setup_pmoves.sh -c full

# Windows PowerShell
.\scripts\setup_pmoves.ps1 -Config full
```

## Prerequisites

### System Requirements
- **Docker Desktop** 4.0+ or Docker Engine 20.10+
- **Docker Compose** V2 (included with Docker Desktop)
- **4GB RAM** minimum (8GB recommended)
- **10GB disk space** for containers and data

### API Keys Required
- **Tailscale Auth Key** (ephemeral recommended)
- **Postman API Key** (for hosted HTTP endpoint)
- **E2B API Key** (for Pro features)
- **OpenAI API Key** (optional, for VL features)

## Configuration Options

### Available Configurations

| Configuration | Features | Use Case |
|---------------|----------|----------|
| `basic` | Docling, Postman, MCP Gateway | Document processing and API testing |
| `pro` | Basic + E2B + VL Sentinel | Research and automated analysis |
| `mini` | Basic + Crush + Discord/Slack | Lightweight agent with notifications |
| `pro-plus` | Basic + Local Postman | Offline Postman integration |
| `full` | All features combined | Complete agent ecosystem |

### Manual Docker Compose

If you prefer manual control:

```bash
# Basic setup
docker compose --env-file .env -f core/docker-compose/base.yml up -d

# Pro setup (Windows/macOS/Linux) with namespace\nexport PMZ_NAMESPACE=botz-dev\nexport COMPOSE_PROJECT_NAME=\ndocker compose --env-file .env \\
  -f core/docker-compose/base.yml \\
  -f features/pro/docker-compose.yml \\
  up -d

# Optional: enable Tailscale on Linux
COMPOSE_PROFILES=linux docker compose \
  -f core/docker-compose/base.yml \
  -f features/pro/docker-compose.yml \
  up -d

### Use PMOVES‑BotZ Gateway (proxy)

To run the new PMOVES‑BotZ gateway instead of the default Python gateway:

```bash
COMPOSE_PROJECT_NAME= docker compose --env-file .env \\
  -f core/docker-compose/base.yml \\
  -f features/pro/docker-compose.yml \\
  -f features/gateway-proxy/docker-compose.yml \\
  up -d
```

By default this proxies Docling at `http://docling-mcp:3020`. To proxy a different MCP server, set:

```bash
export MCP_PROXY_URL=http://host:port
```

# Full setup
docker compose --env-file .env \
  -f core/docker-compose/base.yml \
  -f features/pro/docker-compose.yml \
  -f features/mini/docker-compose.yml \
  -f features/pro-plus/docker-compose.yml \
  up -d
```

## Environment Configuration

### Core Environment Variables

Create a `.env` file with your API keys:

```bash
# Copy from template
cp core/example.env .env

# Edit with your values
TS_AUTHKEY=your_tailscale_key
POSTMAN_API_KEY=your_postman_key
```

### Feature-Specific Variables

#### Pro Features
```bash
# Add to .env
E2B_API_KEY=your_e2b_key
VL_PROVIDER=ollama  # or openai
VL_MODEL=qwen2.5-vl:14b
OLLAMA_BASE_URL=http://host.docker.internal:11434
OPENAI_API_KEY=your_openai_key
```

> Tip: If you have a newer release such as `qwen3-vl`, set `VL_MODEL` to match the artifact you pulled into Ollama.

#### Mini Features
```bash
# Add to .env
SLACK_BOT_TOKEN=your_slack_token
DISCORD_WEBHOOK_URL=your_discord_webhook
CRUSH_API_KEY=your_crush_key
```

## Service Architecture

### Core Services (Always Running)

#### Tailscale
- **Purpose**: Secure networking and HTTPS access
- **Port**: Host network mode
- **Configuration**: Ephemeral auth keys recommended

#### MCP Gateway
- **Purpose**: Aggregates MCP tools for ChatGPT Desktop
- **Port**: 2091 (served via Tailscale HTTPS)
- **Catalog**: `core/mcp_catalog.yaml`

#### Docling MCP
- **Purpose**: Document parsing and extraction
- **Port**: 3020
- **Data**: Persisted in `./data/docling/`

### Optional Services

#### E2B Runner (Pro)
- **Purpose**: Sandboxed code execution
- **Port**: 7071
- **Configuration**: Configurable TTL and API key

#### VL Sentinel (Pro)
- **Purpose**: Vision-language analysis
- **Port**: 7072
- **Providers**: Ollama or OpenAI

#### Local Postman MCP (Pro-Plus)
- **Purpose**: Offline Postman integration
- **Port**: Host network (STDIO mode)
- **Note**: Requires MCP client with process support

## KiloCode Modes

The system includes several specialized modes for different workflows:

### Core Modes
- **Docling Analyst**: Document parsing and API extraction
- **Postman Executor**: API testing and collection management
- **Orchestrator**: Routes tasks between specialized modes

### Pro Modes
- **Auto Research**: Automated research with E2B and VL
- **Code Runner**: Secure code execution in sandboxes

### Advanced Modes
- **VL Guard**: Vision-language monitoring and safety

## Troubleshooting

### Common Issues

#### Services Won't Start
```bash
# Check logs
docker compose logs

# Check service status
docker compose ps

# Restart services
docker compose restart
```

#### API Key Issues
```bash
# Validate environment variables
docker compose exec mcp-gateway env | grep API

# Check service logs for authentication errors
docker compose logs mcp-gateway
```

#### Network Issues
```bash
# Check Tailscale status
docker compose exec tailscale tailscale status

# Verify HTTPS access
curl -k https://your-tailnet-hostname
```

#### Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :3020

# Modify ports in docker-compose files
# Edit features/*/docker-compose.yml
```

### Performance Tuning

#### Memory Issues
```bash
# Increase Docker memory limit
# Docker Desktop: Settings > Resources > Memory

# Limit service memory
# Add to docker-compose.yml:
# services:
#   docling-mcp:
#     deploy:
#       resources:
#         limits:
#           memory: 2G
```

#### Storage Issues
```bash
# Check disk usage
docker system df

# Clean up unused containers
docker system prune -a

# Monitor data directory
du -sh ./data/
```

## Advanced Configuration

### Custom MCP Catalogs

Create custom MCP server configurations:

```yaml
# features/custom/mcp_catalog.yaml
mcpServers:
  custom-tool:
    command: custom-mcp-server
    args: ["--config", "/app/config.json"]
    env:
      CUSTOM_API_KEY: ${CUSTOM_API_KEY}
```

### Environment Inheritance

Environment variables are loaded in this order:
1. `core/example.env` (base defaults)
2. `features/*/example.env` (feature defaults)
3. `.env` (user overrides)
4. System environment

### Custom Docker Compose

Extend the base configuration:

```yaml
# features/custom/docker-compose.yml
version: '3.9'
services:
  custom-service:
    image: custom-image
    environment:
      - CUSTOM_VAR=${CUSTOM_VAR}
    depends_on:
      - mcp-gateway
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check all services
docker compose ps

# Monitor resource usage
docker stats

# View logs
docker compose logs -f mcp-gateway
```

### Backup and Recovery

```bash
# Backup data
tar -czf backup.tar.gz ./data/ .env

# Backup configurations
git add .
git commit -m "Backup configurations"
```

### Updates

```bash
# Pull latest images
docker compose pull

# Restart with updates
docker compose up -d

# Check for configuration changes
git status
```

## Integration Examples

### ChatGPT Desktop Integration

1. **Install ChatGPT Desktop**
2. **Configure MCP Gateway**:
   - URL: `https://your-tailnet-hostname`
   - Authentication: None required (Tailscale handles security)
3. **Select Modes**: Choose appropriate KiloCode modes for your workflow

### Custom Client Integration

```python
import requests

# Connect to MCP Gateway
gateway_url = "https://your-tailnet-hostname"
response = requests.get(f"{gateway_url}/health")
print(f"Gateway status: {response.status_code}")
```

## Security Considerations

### API Key Management
- Use environment variables, never commit to git
- Rotate keys regularly
- Use read-only keys when possible

### Network Security
- Tailscale provides end-to-end encryption
- Limit service exposure to necessary ports
- Use firewall rules to restrict access

### Container Security
- Keep images updated
- Use non-root users where possible
- Monitor for security vulnerabilities

## Support and Resources

### Documentation
- [Migration Plan](MIGRATION_PLAN.md)
- [Docker Compose Design](DOCKER_COMPOSE_DESIGN.md)
- [Feature Flags](config/feature-flags.md)

### Getting Help
- Check service logs: `docker compose logs`
- Validate configuration: `docker compose config`
- Community forums (link TBD)

### Contributing
- Report issues on GitHub
- Submit feature requests
- Contribute documentation improvements

---

**Need help?** Start with the basic configuration and gradually add features. Check the logs if you encounter issues, and refer to the troubleshooting section above.

