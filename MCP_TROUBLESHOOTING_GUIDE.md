# MCP Server Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting steps for resolving common issues with MCP (Model Context Protocol) server implementation in the PMOVES Multi-Agent Pro Pack.

## Quick Diagnostic Commands

### Service Status Check
```bash
# Check all service statuses
docker compose -f docker-compose.mcp-pro.yml ps

# Check individual service logs
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1
docker logs pmoves_multi_agent_pro_pack-mcp-gateway-1
docker logs pmoves_multi_agent_pro_pack-e2b-runner-1
docker logs pmoves_multi_agent_pro_pack-vl-sentinel-1

# Follow logs in real-time
docker compose -f docker-compose.mcp-pro.yml logs -f docling-mcp
```

### Network Connectivity Test
```bash
# Test docling-mcp HTTP endpoint
curl -v -H "Accept: text/event-stream" http://localhost:3020/mcp

# Test mcp-gateway endpoint
curl -v http://localhost:2091/health

# Test service-to-service connectivity from within containers
docker exec -it pmoves_multi_agent_pro_pack-mcp-gateway-1 curl http://docling-mcp:3020/mcp
```

## Common Issues and Solutions

### Issue 1: Docling-MCP Service Fails to Start

**Symptoms:**
- Service shows as "unhealthy" or "restarting"
- Logs show MCP server initialization errors
- HTTP endpoint returns 502/503 errors

**Diagnostic Steps:**
```bash
# Check specific error messages
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -i error

# Check if docling submodule is properly initialized
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 ls -la /srv/docling/

# Test Python imports
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "import mcp; print(mcp.__version__)"
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "from docling.cli.main import convert; print('Docling import successful')"
```

**Solutions:**

1. **Fix MCP API Usage** (Most Common):
```python
# In docling_mcp_server.py, replace incorrect server.run() call:
# INCORRECT:
await server.server.run(transport, server.server.create_initialization_options())

# CORRECT:
async with stdio_server() as (read_stream, write_stream):
    await server.server.run(read_stream, write_stream, server.server.create_initialization_options())
```

2. **Fix HTTP Transport Implementation**:
```python
# For HTTP transport, use proper SSE implementation:
from mcp.server.sse import SseServerTransport

async def run_http_server(server: DoclingMCPServer, host: str = "0.0.0.0", port: int = 3020):
    server.setup_handlers()
    
    # Create proper SSE transport
    transport = SseServerTransport(f"http://{host}:{port}/mcp")
    
    # Start the transport with proper session handling
    await transport.start_server(
        host=host,
        port=port,
        handle_mcp_session=lambda streams: server.server.run(
            streams[0],  # read_stream
            streams[1],  # write_stream
            server.server.create_initialization_options()
        )
    )
```

3. **Rebuild with Fixed Implementation**:
```bash
# Stop the service
docker compose -f docker-compose.mcp-pro.yml stop docling-mcp

# Rebuild with fixes
docker compose -f docker-compose.mcp-pro.yml build docling-mcp

# Start with dependency check
docker compose -f docker-compose.mcp-pro.yml up docling-mcp
```

### Issue 2: MCP Gateway Connection Failures

**Symptoms:**
- Gateway shows "connection refused" to docling-mcp
- Catalog file not found errors
- Service dependency failures

**Diagnostic Steps:**
```bash
# Check gateway logs for connection errors
docker logs pmoves_multi_agent_pro_pack-mcp-gateway-1 | grep -i "docling\|connection\|error"

# Verify catalog file exists
docker exec -it pmoves_multi_agent_pro_pack-mcp-gateway-1 ls -la /app/mcp_catalog_multi.yaml

# Test network connectivity between services
docker exec -it pmoves_multi_agent_pro_pack-mcp-gateway-1 ping docling-mcp
docker exec -it pmoves_multi_agent_pro_pack-mcp-gateway-1 curl -v http://docling-mcp:3020/mcp
```

**Solutions:**

1. **Fix Catalog Configuration**:
```yaml
# In mcp_catalog_multi.yaml, ensure proper endpoint:
servers:
  docling:
    type: http
    url: http://docling-mcp:3020/mcp  # Add /mcp endpoint
    timeout: 60  # Increase timeout
    retries: 5   # Increase retries
```

2. **Fix Service Dependencies**:
```yaml
# In docker-compose.mcp-pro.yml, ensure proper depends_on:
services:
  mcp-gateway:
    depends_on:
      docling-mcp:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2091/health"]
      interval: 30s
      timeout: 10s
      retries: 5  # Increase retries
      start_period: 60s  # Increase start period
```

3. **Manual Service Startup Order**:
```bash
# Start services in correct order with delays
docker compose -f docker-compose.mcp-pro.yml up -d docling-mcp
sleep 30  # Wait for docling-mcp to be ready
docker compose -f docker-compose.mcp-pro.yml up -d mcp-gateway
docker compose -f docker-compose.mcp-pro.yml up -d e2b-runner vl-sentinel
```

### Issue 3: Health Check Failures

**Symptoms:**
- Services show as "unhealthy"
- Frequent restarts
- Connection timeouts

**Diagnostic Steps:**
```bash
# Check health check details
docker inspect pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -A 10 Health

# Test health check endpoint manually
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 curl -f -H "Accept: text/event-stream" http://localhost:3020/mcp

# Check if service is actually running despite health check failure
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 ps aux | grep python
```

**Solutions:**

1. **Fix Health Check Endpoint**:
```dockerfile
# In Dockerfile.docling-mcp, fix health check:
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:3020/mcp || exit 1
```

2. **Increase Health Check Timeouts**:
```yaml
# In docker-compose.mcp-pro.yml:
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3020/mcp"]
  interval: 30s
  timeout: 15s
  retries: 5
  start_period: 60s  # Increase for slower systems
```

### Issue 4: SSE Transport Problems

**Symptoms:**
- SSE connections drop frequently
- No streaming data received
- Browser/client connection issues

**Diagnostic Steps:**
```bash
# Test SSE endpoint with proper headers
curl -N -H "Accept: text/event-stream" -H "Cache-Control: no-cache" http://localhost:3020/mcp

# Check for proper SSE format
curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp | head -20

# Test with different clients
# Browser: Visit http://localhost:3020/mcp and check Network tab
# Python: Use requests with stream=True
```

**Solutions:**

1. **Implement Proper SSE Headers**:
```python
# Ensure proper SSE response headers
headers = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Cache-Control, Accept",
    "Access-Control-Allow-Methods": "GET, OPTIONS"
}
```

2. **Handle CORS Properly**:
```python
# Add CORS handling for browser clients
from mcp.server.cors import cors_middleware

# Apply CORS middleware if available, or implement manually
```

## Advanced Troubleshooting

### Environment Variable Issues

**Check Required Variables:**
```bash
# Verify environment variables are set
docker exec -it pmoves_multi_agent_pro_pack-mcp-gateway-1 env | grep -E "POSTMAN_API_KEY|E2B_API_KEY"

# Check if variables are properly substituted in config files
docker exec -it pmoves_multi_agent_pro_pack-mcp-gateway-1 cat /app/mcp_catalog_multi.yaml | grep -i bearer
```

### Dependency and Import Issues

**Python Import Debugging:**
```bash
# Check Python path and available modules
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "import sys; print(sys.path)"

# Test specific imports
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "
try:
    from mcp.server import Server
    print('MCP Server import: OK')
except ImportError as e:
    print(f'MCP Server import failed: {e}')

try:
    from docling.cli.main import convert
    print('Docling import: OK')
except ImportError as e:
    print(f'Docling import failed: {e}')
"
```

### Network and Port Issues

**Port Availability Check:**
```bash
# Check if ports are already in use
netstat -an | grep -E "3020|2091|7071|7072"

# Test port connectivity
telnet localhost 3020
nc -zv localhost 3020
```

### Docker-Specific Issues

**Container Resource Issues:**
```bash
# Check container resource usage
docker stats pmoves_multi_agent_pro_pack-docling-mcp-1

# Check container logs for resource-related errors
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -i "memory\|oom\|killed"

# Increase container memory if needed
# In docker-compose.mcp-pro.yml:
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 512M
```

## Recovery Procedures

### Complete Service Reset

```bash
# Stop all services
docker compose -f docker-compose.mcp-pro.yml down

# Remove all containers and volumes (CAREFUL - deletes data)
docker compose -f docker-compose.mcp-pro.yml down -v

# Clean up Docker system
docker system prune -f

# Rebuild and restart
docker compose -f docker-compose.mcp-pro.yml build --no-cache
docker compose -f docker-compose.mcp-pro.yml up -d
```

### Individual Service Recovery

```bash
# Reset specific service
docker compose -f docker-compose.mcp-pro.yml stop docling-mcp
docker compose -f docker-compose.mcp-pro.yml rm docling-mcp
docker compose -f docker-compose.mcp-pro.yml build docling-mcp
docker compose -f docker-compose.mcp-pro.yml up -d docling-mcp
```

## Monitoring and Maintenance

### Log Monitoring Setup

```bash
# Create monitoring script
cat > monitor_mcp_services.sh << 'EOF'
#!/bin/bash
while true; do
    echo "=== MCP Services Status - $(date) ==="
    docker compose -f docker-compose.mcp-pro.yml ps
    
    echo "=== Recent Errors ==="
    for service in docling-mcp mcp-gateway e2b-runner vl-sentinel; do
        echo "--- $service ---"
        docker logs pmoves_multi_agent_pro_pack-${service}-1 --tail 10 | grep -i error || echo "No recent errors"
    done
    
    echo "=== Health Check Status ==="
    curl -f http://localhost:3020/mcp > /dev/null 2>&1 && echo "Docling-MCP: OK" || echo "Docling-MCP: FAILED"
    curl -f http://localhost:2091/health > /dev/null 2>&1 && echo "MCP-Gateway: OK" || echo "MCP-Gateway: FAILED"
    
    sleep 60
done
EOF

chmod +x monitor_mcp_services.sh
./monitor_mcp_services.sh
```

### Performance Monitoring

```bash
# Monitor service performance
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# Check response times
time curl -s http://localhost:3020/mcp > /dev/null
time curl -s http://localhost:2091/health > /dev/null
```

## Getting Help

### Information to Collect

When reporting issues, provide:

1. **Service Status**: Output of `docker compose -f docker-compose.mcp-pro.yml ps`
2. **Error Logs**: Relevant error messages from service logs
3. **Configuration**: Your `mcp_catalog_multi.yaml` and relevant environment variables
4. **System Info**: Docker version, OS, available resources
5. **Reproduction Steps**: Exact commands that led to the issue

### Debug Information Script

```bash
# Create comprehensive debug info
cat > collect_debug_info.sh << 'EOF'
#!/bin/bash
echo "=== MCP Debug Information Collection ==="
echo "Date: $(date)"
echo "System: $(uname -a)"
echo "Docker Version: $(docker --version)"
echo ""

echo "=== Service Status ==="
docker compose -f docker-compose.mcp-pro.yml ps
echo ""

echo "=== Recent Logs (last 50 lines) ==="
for service in docling-mcp mcp-gateway e2b-runner vl-sentinel; do
    echo "--- $service ---"
    docker logs pmoves_multi_agent_pro_pack-${service}-1 --tail 50
    echo ""
done

echo "=== Network Connectivity ==="
echo "Testing docling-mcp endpoint:"
curl -v -H "Accept: text/event-stream" http://localhost:3020/mcp 2>&1 | head -20
echo ""
echo "Testing mcp-gateway endpoint:"
curl -v http://localhost:2091/health 2>&1 | head -20
echo ""

echo "=== Container Resource Usage ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
EOF

chmod +x collect_debug_info.sh
./collect_debug_info.sh > mcp_debug_info.txt
```

This comprehensive troubleshooting guide should help resolve most common MCP server implementation issues. Start with the quick diagnostic commands and work through the specific issue sections as needed.