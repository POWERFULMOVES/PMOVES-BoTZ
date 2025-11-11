# 🚀 Service Launch Script

## Phase 1: Core Infrastructure Services

### 1. Start Tailscale VPN
```bash
cd pmoves_multi_agent_pro_pack
docker-compose -f docker-compose.mcp-pro.yml up tailscale -d
```

### 2. Start Docling MCP Server (already running)
```bash
docker-compose -f docker-compose.mcp-pro.yml up docling-mcp -d
```

### 3. Start MCP Gateway
```bash
docker-compose -f docker-compose.mcp-pro.yml up mcp-gateway -d
```

## Phase 2: Specialized Services

### 4. Start E2B Runner
```bash
docker-compose -f docker-compose.mcp-pro.yml up e2b-runner -d
```

### 5. Start VL Sentinel
```bash
docker-compose -f docker-compose.mcp-pro.yml up vl-sentinel -d
```

### 6. Start Cipher Memory
```bash
docker-compose -f docker-compose.mcp-pro.yml up cipher-memory -d
```

## Phase 3: Pro Plus Extensions

### 7. Start Postman MCP Local
```bash
cd pmoves_multi_agent_pro_plus_pack
docker-compose -f docker-compose.mcp-pro.local-postman.yml up postman-mcp-local -d
```

### 8. Start VLM-enhanced Docling
```bash
docker-compose -f docker-compose.mcp-pro.vlm.yml up docling-mcp -d
```

## Health Check Commands

### Check All Services
```bash
# Check service status
docker-compose -f docker-compose.mcp-pro.yml ps

# Individual health checks
curl -H "Accept: text/event-stream" -f http://localhost:3020/health
curl -f http://localhost:2091/health
curl -f http://localhost:7071/health
curl -f http://localhost:7072/health
curl -f http://localhost:8080/health
```

### Quick Status Script
```bash
#!/bin/bash
echo "🔍 Checking all service health..."

services=(
    "docling-mcp:3020"
    "mcp-gateway:2091"
    "e2b-runner:7071"
    "vl-sentinel:7072"
    "cipher-memory:8080"
)

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    echo -n "Checking $name on port $port... "
    if curl -s -f "http://localhost:$port/health" > /dev/null; then
        echo "✅ Healthy"
    else
        echo "❌ Unhealthy"
    fi
done
```

## Service Management

### View Logs
```bash
docker-compose -f docker-compose.mcp-pro.yml logs -f <service-name>
```

### Restart Service
```bash
docker-compose -f docker-compose.mcp-pro.yml restart <service-name>
```

### Stop All Services
```bash
docker-compose -f docker-compose.mcp-pro.yml down
```

## Environment Variables Required

### Core Services
- TAILSCALE_AUTHKEY
- E2B_API_KEY
- VL_PROVIDER (ollama/openai)
- VL_MODEL
- OLLAMA_BASE_URL
- OPENAI_API_KEY
- VENICE_API_KEY

### Optional
- POSTMAN_API_KEY