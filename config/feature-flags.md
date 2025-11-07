# PMOVES Feature Flags Configuration

## Environment-Based Feature Activation

Features are activated by setting environment variables in your `.env` file. Each feature flag corresponds to a Docker Compose override file.

## Available Features

### Core Features (Always Active)
- **Tailscale**: Network connectivity and HTTPS serving
- **MCP Gateway**: Aggregates MCP tools for ChatGPT Desktop
- **Docling MCP**: Document parsing and extraction

### Optional Features

#### PRO Features
Set `PMOVES_FEATURE_PRO=true` to enable:
- **E2B Runner**: Sandboxed code execution
- **VL Sentinel**: Vision-language analysis and monitoring

Environment variables required:
```bash
# E2B Sandbox
E2B_API_KEY=your_key_here
SANDBOX_TTL_SEC=1800

# Vision-Language
VL_PROVIDER=ollama  # or openai
VL_MODEL=qwen2.5-vl:14b
OLLAMA_BASE_URL=http://host.docker.internal:11434
OPENAI_API_KEY=your_key_here
```

#### MINI Features
Set `PMOVES_FEATURE_MINI=true` to enable:
- **Crush MCP**: Additional MCP server for mini agent box
- **Discord Bot**: Discord integration
- **Slack Integration**: Slack notifications

Environment variables required:
```bash
SLACK_BOT_TOKEN=your_token
DISCORD_WEBHOOK_URL=your_webhook
CRUSH_API_KEY=your_key
```

#### PRO-PLUS Features
Set `PMOVES_FEATURE_PRO_PLUS=true` to enable:
- **Local Postman MCP**: STDIO-based Postman integration

Environment variables required:
```bash
POSTMAN_API_KEY=your_key
```

## Configuration Examples

### Basic Setup (Core Only)
```bash
# .env
TS_AUTHKEY=your_tailscale_key
POSTMAN_API_KEY=your_postman_key
```

### Pro Setup (Core + Pro Features)
```bash
# .env
TS_AUTHKEY=your_tailscale_key
POSTMAN_API_KEY=your_postman_key
PMOVES_FEATURE_PRO=true
E2B_API_KEY=your_e2b_key
VL_PROVIDER=ollama
```

### Full Setup (All Features)
```bash
# .env
TS_AUTHKEY=your_tailscale_key
POSTMAN_API_KEY=your_postman_key
PMOVES_FEATURE_PRO=true
PMOVES_FEATURE_MINI=true
PMOVES_FEATURE_PRO_PLUS=true

# Pro features
E2B_API_KEY=your_e2b_key
VL_PROVIDER=ollama

# Mini features
SLACK_BOT_TOKEN=your_slack_token
DISCORD_WEBHOOK_URL=your_discord_webhook
CRUSH_API_KEY=your_crush_key
```

## Docker Compose Commands

### Start with Feature Flags
```bash
# Core only
docker compose -f core/docker-compose/base.yml up

# With Pro features
docker compose -f core/docker-compose/base.yml -f features/pro/docker-compose.yml up

# Full stack
docker compose \
  -f core/docker-compose/base.yml \
  -f features/pro/docker-compose.yml \
  -f features/mini/docker-compose.yml \
  -f features/pro-plus/docker-compose.yml \
  up
```

### Conditional Compose (Recommended)
Use a setup script that reads feature flags and composes the appropriate files:

```bash
#!/bin/bash
COMPOSE_FILES="-f core/docker-compose/base.yml"

if [ "$PMOVES_FEATURE_PRO" = "true" ]; then
  COMPOSE_FILES="$COMPOSE_FILES -f features/pro/docker-compose.yml"
fi

if [ "$PMOVES_FEATURE_MINI" = "true" ]; then
  COMPOSE_FILES="$COMPOSE_FILES -f features/mini/docker-compose.yml"
fi

if [ "$PMOVES_FEATURE_PRO_PLUS" = "true" ]; then
  COMPOSE_FILES="$COMPOSE_FILES -f features/pro-plus/docker-compose.yml"
fi

docker compose $COMPOSE_FILES up