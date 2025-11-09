# Comprehensive Troubleshooting Guide for Docling MCP Service

This guide provides comprehensive troubleshooting procedures for resolving common issues with the docling-mcp service implementation. It covers connection problems, performance issues, configuration errors, document processing failures, MCP protocol issues, and deployment problems.

## Table of Contents

1. [Quick Diagnostic Commands](#quick-diagnostic-commands)
2. [Connection Issues](#connection-issues)
3. [Performance Issues](#performance-issues)
4. [Configuration Problems](#configuration-problems)
5. [Document Processing Issues](#document-processing-issues)
6. [MCP Protocol Issues](#mcp-protocol-issues)
7. [Deployment Issues](#deployment-issues)
8. [Diagnostic Tools and Procedures](#diagnostic-tools-and-procedures)
9. [Resolution Strategies](#resolution-strategies)
10. [Preventive Measures](#preventive-measures)
11. [Troubleshooting Scripts](#troubleshooting-scripts)

## Quick Diagnostic Commands

### Service Status Check
```bash
# Check all service statuses
docker compose -f docker-compose.mcp-pro.yml ps

# Check individual service logs
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 --tail 50
docker logs pmoves_multi_agent_pro_pack-mcp-gateway-1 --tail 50

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

### Health Check Verification
```bash
# Check health endpoints
curl http://localhost:3020/health
curl http://localhost:2091/health

# Check metrics availability
curl http://localhost:3020/metrics
curl http://localhost:3020/dashboard
```

## Connection Issues

### SSE Connection Failures

**Symptoms:**
- SSE connections drop immediately
- "Connection refused" errors
- No streaming data received
- Browser/client connection timeouts

**Diagnostic Steps:**
```bash
# Check if docling-mcp is running
docker ps | grep docling-mcp

# Test SSE endpoint with proper headers
curl -N -H "Accept: text/event-stream" -H "Cache-Control: no-cache" http://localhost:3020/mcp

# Check for proper SSE format
curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp | head -20

# Verify port availability
netstat -an | grep 3020
```

**Resolution Strategies:**

1. **Fix SSE Headers Configuration**:
   ```yaml
   # In config/default.yaml or environment variables
   sse:
     endpoint: "/mcp"
     keepalive_interval: 0.1
     connection_timeout: 30.0
     cors_origins: ["*"]
     cors_methods: ["GET", "OPTIONS"]
     cors_headers: ["Content-Type", "Accept", "Cache-Control"]
   ```

2. **Check Custom SSE Handler Implementation**:
   ```python
   # Verify create_custom_sse_handler is properly implemented
   # Check for proper response headers:
   headers = {
       "Content-Type": "text/event-stream",
       "Cache-Control": "no-cache",
       "Connection": "keep-alive",
       "Access-Control-Allow-Origin": "*"
   }
   ```

3. **Fix Docker Network Issues**:
   ```bash
   # Rebuild with proper networking
   docker compose -f docker-compose.mcp-pro.yml down
   docker compose -f docker-compose.mcp-pro.yml build docling-mcp
   docker compose -f docker-compose.mcp-pro.yml up docling-mcp
   ```

### Timeout Problems

**Symptoms:**
- Connections timeout after 30 seconds
- Intermittent connection drops
- Slow response times

**Diagnostic Steps:**
```bash
# Check timeout configuration
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 env | grep -i timeout

# Test with increased timeout
curl -m 60 -H "Accept: text/event-stream" http://localhost:3020/mcp

# Monitor connection duration
time curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp
```

**Resolution Strategies:**

1. **Adjust Timeout Configuration**:
   ```yaml
   sse:
     connection_timeout: 60.0  # Increase from 30.0
     keepalive_interval: 0.5   # Increase from 0.1
   
   performance:
     tool_timeout: 60.0  # Increase from 30.0
   ```

2. **Environment Variables**:
   ```bash
   DOCLING_MCP_SSE__CONNECTION_TIMEOUT=60.0
   DOCLING_MCP_PERFORMANCE__TOOL_TIMEOUT=60.0
   ```

### CORS Errors

**Symptoms:**
- Browser shows CORS errors
- Cross-origin requests blocked
- OPTIONS requests failing

**Diagnostic Steps:**
```bash
# Test CORS preflight
curl -X OPTIONS -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  http://localhost:3020/mcp

# Check response headers
curl -I -X OPTIONS http://localhost:3020/mcp
```

**Resolution Strategies:**

1. **Fix CORS Configuration**:
   ```yaml
   security:
     enable_cors: true
     allowed_origins: ["http://localhost:3000", "https://yourdomain.com"]
   
   sse:
     cors_origins: ["http://localhost:3000", "https://yourdomain.com"]
     cors_methods: ["GET", "OPTIONS"]
     cors_headers: ["Content-Type", "Accept", "Cache-Control", "Authorization"]
   ```

2. **Environment Variables**:
   ```bash
   DOCLING_MCP_SECURITY__ENABLE_CORS=true
   DOCLING_MCP_SECURITY__ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
   ```

## Performance Issues

### Slow Response Times

**Symptoms:**
- Tool execution takes >30 seconds
- High P95 response times
- Client timeouts

**Diagnostic Steps:**
```bash
# Check response times
time curl http://localhost:3020/health

# Monitor resource usage
docker stats pmoves_multi_agent_pro_pack-docling-mcp-1

# Check metrics for performance data
curl http://localhost:3020/metrics | grep response_time
```

**Resolution Strategies:**

1. **Optimize Performance Configuration**:
   ```yaml
   performance:
     tool_timeout: 60.0
     max_connections: 200
     rate_limit_requests: 1000
     rate_limit_window: 3600
   ```

2. **Enable Metrics Monitoring**:
   ```yaml
   metrics:
     enabled: true
     collection_interval: 10.0
     alert_thresholds:
       response_time_p95:
         warning: 1000.0
         critical: 2000.0
   ```

3. **Resource Optimization**:
   ```yaml
   docling:
     enable_cache: true
     cache_dir: "/data/cache"
     max_file_size: 52428800  # 50MB limit
   ```

### Memory Leaks

**Symptoms:**
- Memory usage continuously increases
- Container restarts due to OOM
- Performance degrades over time

**Diagnostic Steps:**
```bash
# Monitor memory usage
docker stats --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" pmoves_multi_agent_pro_pack-docling-mcp-1

# Check for memory leaks in logs
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -i "memory\|oom"

# Monitor Python memory usage
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

**Resolution Strategies:**

1. **Configure Metrics Collection**:
   ```yaml
   metrics:
     enabled: true
     collection_interval: 10.0
     retention_hours: 24
     storage_backend: "file"
     compression_enabled: true
   ```

2. **Adjust Resource Limits**:
   ```yaml
   # In docker-compose.mcp-pro.yml
   deploy:
     resources:
       limits:
         memory: 1G
       reservations:
         memory: 512M
   ```

3. **Enable Cache Management**:
   ```yaml
   docling:
     enable_cache: true
     cache_dir: "/data/cache"
     max_file_size: 52428800
   ```

### High CPU Usage

**Symptoms:**
- CPU usage consistently >80%
- System becomes unresponsive
- Other services affected

**Diagnostic Steps:**
```bash
# Monitor CPU usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}" pmoves_multi_agent_pro_pack-docling-mcp-1

# Check process CPU usage
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 top

# Monitor CPU-intensive operations
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 ps aux --sort=-%cpu
```

**Resolution Strategies:**

1. **Optimize Configuration**:
   ```yaml
   performance:
     max_connections: 100  # Reduce if too high
     tool_timeout: 30.0     # Reduce if too long
   
   metrics:
     collection_interval: 30.0  # Increase to reduce overhead
   ```

2. **Enable CPU Monitoring**:
   ```yaml
   metrics:
     alert_thresholds:
       cpu_usage_percent:
         warning: 70.0
         critical: 85.0
   ```

## Configuration Problems

### Invalid Settings

**Symptoms:**
- Service fails to start
- Configuration validation errors
- Default values used instead of custom settings

**Diagnostic Steps:**
```bash
# Check configuration loading
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -i "config\|error"

# Verify environment variables
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 env | grep DOCLING_MCP

# Test configuration validation
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "
from config import load_config
try:
    config = load_config()
    print('Configuration loaded successfully')
except Exception as e:
    print(f'Configuration error: {e}')
"
```

**Resolution Strategies:**

1. **Create Default Configuration**:
   ```bash
   # Generate default configuration files
   docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python docling_mcp_server.py --create-config
   ```

2. **Fix Configuration Syntax**:
   ```yaml
   # Ensure proper YAML syntax
   server:
     host: "0.0.0.0"
     port: 3020
     transport: "http"
   
   logging:
     level: "INFO"
     format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
   ```

3. **Environment Variable Fixes**:
   ```bash
   # Use correct naming convention
   DOCLING_MCP_SERVER__HOST=0.0.0.0
   DOCLING_MCP_SERVER__PORT=3020
   DOCLING_MCP_LOGGING__LEVEL=INFO
   ```

### Environment Variable Issues

**Symptoms:**
- Environment variables not applied
- Default configuration used
- Incorrect values in effect

**Diagnostic Steps:**
```bash
# Check environment variables in container
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 env | grep DOCLING_MCP

# Verify variable substitution
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "
import os
print(f'Transport: {os.getenv(\"DOCLING_MCP_SERVER__TRANSPORT\", \"not set\")}')
print(f'Port: {os.getenv(\"DOCLING_MCP_SERVER__PORT\", \"not set\")}')
"
```

**Resolution Strategies:**

1. **Fix Environment Variable Names**:
   ```bash
   # Correct format: DOCLING_MCP__SECTION__KEY
   DOCLING_MCP_SERVER__TRANSPORT=http
   DOCLING_MCP_SERVER__PORT=3020
   DOCLING_MCP_LOGGING__LEVEL=DEBUG
   ```

2. **Update Docker Compose**:
   ```yaml
   # In docker-compose.mcp-pro.yml
   environment:
     DOCLING_MCP_SERVER__TRANSPORT: ${DOCLING_MCP_TRANSPORT:-http}
     DOCLING_MCP_SERVER__PORT: ${DOCLING_MCP_PORT:-3020}
     DOCLING_MCP_LOGGING__LEVEL: ${DOCLING_MCP_LOG_LEVEL:-INFO}
   ```

### Docker Configuration Issues

**Symptoms:**
- Container fails to start
- Volume mounting problems
- Port binding errors

**Diagnostic Steps:**
```bash
# Check Docker configuration
docker compose -f docker-compose.mcp-pro.yml config

# Verify volume mounts
docker volume ls | grep docling

# Check port conflicts
netstat -an | grep -E "3020|2091"
```

**Resolution Strategies:**

1. **Fix Volume Mounts**:
   ```yaml
   # In docker-compose.mcp-pro.yml
   volumes:
     - ./data/docling:/data
     - ./config:/srv/config:ro
     - docling_logs:/var/log
   ```

2. **Fix Port Configuration**:
   ```yaml
   ports:
     - "3020:3020"
   
   # Or use different host port
   ports:
     - "8080:3020"
   ```

3. **Rebuild with Clean State**:
   ```bash
   docker compose -f docker-compose.mcp-pro.yml down -v
   docker compose -f docker-compose.mcp-pro.yml build --no-cache
   docker compose -f docker-compose.mcp-pro.yml up
   ```

## Document Processing Issues

### Docling Import Errors

**Symptoms:**
- "Docling not available" errors
- Import failures
- Document conversion not working

**Diagnostic Steps:**
```bash
# Check Docling installation
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "
try:
    from docling.document_converter import DocumentConverter
    print('Docling import: OK')
except ImportError as e:
    print(f'Docling import failed: {e}')
"

# Check Docling version
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "
import docling
print(f'Docling version: {docling.__version__}')
"
```

**Resolution Strategies:**

1. **Rebuild with Docling**:
   ```bash
   # Rebuild Docker image with Docling
   docker compose -f docker-compose.mcp-pro.yml build --no-cache docling-mcp
   
   # Verify Docling submodule
   git submodule update --init --recursive
   ```

2. **Fix Dockerfile**:
   ```dockerfile
   # In Dockerfile.docling-mcp
   COPY docling/ ./docling/
   RUN pip install --no-cache-dir ./docling/
   ```

3. **Check Requirements**:
   ```bash
   # Verify docling_mcp_requirements.txt
   cat docling_mcp_requirements.txt
   
   # Install missing dependencies
   pip install docling
   ```

### File Access Issues

**Symptoms:**
- "File not found" errors
- Permission denied errors
- Cannot access document files

**Diagnostic Steps:**
```bash
# Check file permissions
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 ls -la /data/

# Test file access
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 touch /data/test.txt

# Check volume mounts
docker inspect pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -A 10 Mounts
```

**Resolution Strategies:**

1. **Fix Volume Permissions**:
   ```bash
   # Set proper permissions
   sudo chown -R 1000:1000 ./data/docling
   chmod -R 755 ./data/docling
   ```

2. **Update Docker Compose**:
   ```yaml
   # In docker-compose.mcp-pro.yml
   volumes:
     - ./data/docling:/data:rw  # Explicit read-write
     - ./config:/srv/config:ro
   ```

3. **Create Required Directories**:
   ```bash
   # Create cache directory
   mkdir -p ./data/docling/cache
   chmod 755 ./data/docling/cache
   ```

### File Size Limitations

**Symptoms:**
- Large files rejected
- "File size exceeds maximum" errors
- Processing timeouts on large files

**Diagnostic Steps:**
```bash
# Check file size limits
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "
from config import load_config
config = load_config()
print(f'Max file size: {config.docling.max_file_size} bytes')
"

# Test with different file sizes
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 ls -lh /data/
```

**Resolution Strategies:**

1. **Adjust File Size Limits**:
   ```yaml
   docling:
     max_file_size: 209715200  # 200MB
   ```

2. **Environment Variables**:
   ```bash
   DOCLING_MCP_DOCLING__MAX_FILE_SIZE=209715200
   ```

3. **Implement Chunked Processing**:
   ```python
   # For very large files, implement chunked processing
   # or use streaming conversion methods
   ```

## MCP Protocol Issues

### JSON-RPC Errors

**Symptoms:**
- Invalid JSON-RPC responses
- Protocol version mismatches
- Tool execution failures

**Diagnostic Steps:**
```bash
# Test MCP protocol compliance
curl -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' \
  http://localhost:3020/mcp

# Check response format
curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp | head -10
```

**Resolution Strategies:**

1. **Fix MCP Server Implementation**:
   ```python
   # Ensure proper JSON-RPC 2.0 compliance
   @self.server.list_tools()
   async def list_tools() -> ListToolsResult:
       return ListToolsResult(tools=tools)
   
   @self.server.call_tool()
   async def call_tool(name: str, arguments: dict) -> CallToolResult:
       # Proper error handling
       try:
           result = await self.execute_tool(name, arguments)
           return result
       except Exception as e:
           return CallToolResult(
               content=[TextContent(type="text", text=f"Error: {str(e)}")],
               isError=True
           )
   ```

2. **Update MCP SDK**:
   ```bash
   # Update to latest MCP SDK
   pip install --upgrade mcp
   ```

### Tool Execution Failures

**Symptoms:**
- Tools not found
- Invalid tool arguments
- Tool execution timeouts

**Diagnostic Steps:**
```bash
# Test tool listing
curl -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' \
  http://localhost:3020/mcp

# Test specific tool
curl -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "health_check", "arguments": {}}, "id": 2}' \
  http://localhost:3020/mcp
```

**Resolution Strategies:**

1. **Fix Tool Registration**:
   ```python
   # Ensure tools are properly registered
   tools = [
       Tool(
           name="convert_document",
           description="Convert documents to structured format",
           inputSchema={
               "type": "object",
               "properties": {
                   "file_path": {"type": "string"},
                   "output_format": {"type": "string", "enum": ["markdown", "text", "json"]}
               },
               "required": ["file_path"]
           }
       )
   ]
   ```

2. **Fix Tool Execution**:
   ```python
   # Implement proper tool execution
   async def execute_tool(self, name: str, arguments: dict) -> CallToolResult:
       if name == "convert_document":
           return await self.convert_document(arguments)
       else:
           return CallToolResult(
               content=[TextContent(type="text", text=f"Unknown tool: {name}")],
               isError=True
           )
   ```

### Session Management Issues

**Symptoms:**
- Sessions not maintained
- Connection drops during processing
- State loss between requests

**Diagnostic Steps:**
```bash
# Test session persistence
curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp &
sleep 5
curl -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "health_check", "arguments": {}}, "id": 3}' \
  http://localhost:3020/mcp
```

**Resolution Strategies:**

1. **Fix Session Handling**:
   ```python
   # Implement proper session management
   async def handle_session(session_streams):
       read_stream, write_stream = session_streams
       try:
           await server.server.run(
               read_stream,
               write_stream,
               server.server.create_initialization_options()
           )
       except Exception as e:
           logger.error(f"Session handling error: {e}")
   ```

2. **Configure Session Timeouts**:
   ```yaml
   sse:
     connection_timeout: 60.0
     keepalive_interval: 0.5
   ```

## Deployment Issues

### Docker Build Failures

**Symptoms:**
- Build fails during Dockerfile execution
- Dependency installation errors
- Missing files in build context

**Diagnostic Steps:**
```bash
# Check build context
docker build -f Dockerfile.docling-mcp -t docling-mcp:test .

# Check build logs
docker build -f Dockerfile.docling-mcp -t docling-mcp:test . 2>&1 | tee build.log

# Verify Dockerfile syntax
docker build -f Dockerfile.docling-mcp --dry-run .
```

**Resolution Strategies:**

1. **Fix Dockerfile**:
   ```dockerfile
   # Ensure proper base image and dependencies
   FROM python:3.11-slim-bullseye
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y curl
   
   # Copy and install docling
   COPY docling/ ./docling/
   RUN pip install --no-cache-dir ./docling/
   
   # Copy application code
   COPY docling_mcp_server.py .
   COPY docling_mcp_requirements.txt .
   RUN pip install --no-cache-dir -r docling_mcp_requirements.txt
   ```

2. **Fix Build Context**:
   ```bash
   # Ensure .dockerignore is properly configured
   echo "node_modules" > .dockerignore
   echo ".git" >> .dockerignore
   echo "*.log" >> .dockerignore
   ```

3. **Rebuild with Clean State**:
   ```bash
   docker system prune -f
   docker compose -f docker-compose.mcp-pro.yml build --no-cache
   ```

### Health Check Problems

**Symptoms:**
- Services show as unhealthy
- Frequent container restarts
- Health check endpoint failures

**Diagnostic Steps:**
```bash
# Test health check manually
curl -f http://localhost:3020/health

# Check health check configuration
docker inspect pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -A 10 Health

# Monitor health status
docker compose -f docker-compose.mcp-pro.yml ps
```

**Resolution Strategies:**

1. **Fix Health Check Endpoint**:
   ```python
   # Implement proper health check
   async def health_check(request):
       try:
           # Check critical components
           health_status = "healthy"
           status_code = 200
           
           return web.Response(
               text=json.dumps({
                   "status": health_status,
                   "timestamp": datetime.now().isoformat(),
                   "docling_available": DOCLING_AVAILABLE
               }),
               content_type="application/json",
               status=status_code
           )
       except Exception as e:
           return web.Response(text="Service Unavailable", status=503)
   ```

2. **Update Docker Configuration**:
   ```yaml
   # In docker-compose.mcp-pro.yml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:3020/health"]
     interval: 30s
     timeout: 15s
     retries: 5
     start_period: 60s
   ```

3. **Fix Dockerfile Health Check**:
   ```dockerfile
   # In Dockerfile.docling-mcp
   HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=5 \
       CMD curl -f http://localhost:3020/health || exit 1
   ```

### Service Startup Errors

**Symptoms:**
- Services fail to start
- Initialization errors
- Missing dependencies

**Diagnostic Steps:**
```bash
# Check startup logs
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1

# Check service dependencies
docker compose -f docker-compose.mcp-pro.yml up --no-deps docling-mcp

# Test manual startup
docker run --rm -it docling-mcp python docling_mcp_server.py --help
```

**Resolution Strategies:**

1. **Fix Service Dependencies**:
   ```yaml
   # In docker-compose.mcp-pro.yml
   depends_on:
     docling-mcp:
       condition: service_healthy
   ```

2. **Fix Startup Script**:
   ```bash
   # In docker-compose.mcp-pro.yml
   command: >
     sh -lc "
     echo 'Starting Docling MCP Server...' &&
     python docling_mcp_server.py --environment production
     "
   ```

3. **Add Startup Delay**:
   ```yaml
   # In docker-compose.mcp-pro.yml
   healthcheck:
     start_period: 60s  # Increase startup time
   ```

## Diagnostic Tools and Procedures

### Step-by-Step Diagnostic Commands

1. **Service Status Check**:
   ```bash
   # Check all services
   docker compose -f docker-compose.mcp-pro.yml ps
   
   # Check individual service health
   docker inspect pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -A 10 Health
   ```

2. **Log Analysis**:
   ```bash
   # Check for errors
   docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 2>&1 | grep -i error
   
   # Check recent logs
   docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 --tail 100
   
   # Follow logs in real-time
   docker logs -f pmoves_multi_agent_pro_pack-docling-mcp-1
   ```

3. **Network Connectivity Testing**:
   ```bash
   # Test endpoint accessibility
   curl -v http://localhost:3020/health
   curl -v http://localhost:2091/health
   
   # Test SSE endpoint
   curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp
   
   # Test service-to-service connectivity
   docker exec -it pmoves_multi_agent_pro_pack-mcp-gateway-1 curl http://docling-mcp:3020/mcp
   ```

4. **Resource Usage Monitoring**:
   ```bash
   # Monitor resource usage
   docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
   
   # Check disk usage
   docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 df -h
   
   # Check memory usage
   docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 free -h
   ```

### Log Analysis Techniques

1. **Error Pattern Analysis**:
   ```bash
   # Extract error patterns
   docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 2>&1 | \
     grep -E "ERROR|CRITICAL|Exception" | \
     awk '{print $1, $2, $NF}' | sort | uniq -c
   ```

2. **Performance Analysis**:
   ```bash
   # Extract response times
   docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 2>&1 | \
     grep "response_time" | \
     awk '{print $NF}' | sort -n | tail -10
   ```

3. **Connection Analysis**:
   ```bash
   # Track connection patterns
   docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 2>&1 | \
     grep "SSE connection" | \
     awk '{print $6}' | sort | uniq -c
   ```

### Performance Monitoring Procedures

1. **Baseline Establishment**:
   ```bash
   # Run performance test
   curl -w "@curl-format.txt" -o /dev/null -s http://localhost:3020/health
   
   # Monitor metrics over time
   for i in {1..60}; do
     curl -s http://localhost:3020/metrics >> metrics.log
     sleep 60
   done
   ```

2. **Load Testing**:
   ```bash
   # Concurrent connections test
   for i in {1..10}; do
     curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp &
   done
   wait
   ```

3. **Resource Profiling**:
   ```bash
   # Profile memory usage
   docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "
import psutil
import time
process = psutil.Process()
for i in range(60):
    print(f'{time.time()},{process.memory_info().rss}')
    time.sleep(1)
" > memory_profile.csv
   ```

## Resolution Strategies

### Quick Fixes for Common Issues

1. **Service Restart**:
   ```bash
   # Restart specific service
   docker compose -f docker-compose.mcp-pro.yml restart docling-mcp
   
   # Restart all services
   docker compose -f docker-compose.mcp-pro.yml restart
   ```

2. **Configuration Reload**:
   ```bash
   # Reload configuration
   docker compose -f docker-compose.mcp-pro.yml down
   docker compose -f docker-compose.mcp-pro.yml up -d
   ```

3. **Cache Clearing**:
   ```bash
   # Clear docling cache
   docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 rm -rf /data/cache/*
   
   # Clear metrics cache
   docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 rm -rf /data/metrics/*
   ```

### Workarounds for Known Problems

1. **SSE Connection Issues**:
   ```bash
   # Use HTTP polling as fallback
   curl -X POST -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' \
     http://localhost:3020/mcp
   ```

2. **Memory Issues**:
   ```bash
   # Increase container memory limit
   docker compose -f docker-compose.mcp-pro.yml down
   # Update docker-compose.mcp-pro.yml with memory limits
   docker compose -f docker-compose.mcp-pro.yml up -d
   ```

3. **Performance Issues**:
   ```bash
   # Disable metrics temporarily
   docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 \
     sed -i 's/enabled: true/enabled: false/' /srv/config/default.yaml
   docker compose -f docker-compose.mcp-pro.yml restart docling-mcp
   ```

### Escalation Procedures

1. **Collect Debug Information**:
   ```bash
   # Create debug bundle
   mkdir -p debug_bundle
   docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 > debug_bundle/docling-mcp.log
   docker compose -f docker-compose.mcp-pro.yml config > debug_bundle/docker-compose.yml
   docker inspect pmoves_multi_agent_pro_pack-docling-mcp-1 > debug_bundle/container-inspect.json
   tar -czf debug_bundle.tar.gz debug_bundle/
   ```

2. **System Health Check**:
   ```bash
   # Check system resources
   df -h > debug_bundle/system-info.txt
   free -h >> debug_bundle/system-info.txt
   uptime >> debug_bundle/system-info.txt
   docker version >> debug_bundle/system-info.txt
   ```

3. **Network Diagnostics**:
   ```bash
   # Check network configuration
   docker network ls > debug_bundle/networks.txt
   docker network inspect pmoves_multi_agent_pro_pack_default >> debug_bundle/networks.txt
   netstat -an | grep -E "3020|2091" >> debug_bundle/networks.txt
   ```

### Recovery Methods

1. **Complete Service Reset**:
   ```bash
   # Stop all services
   docker compose -f docker-compose.mcp-pro.yml down
   
   # Remove volumes (CAREFUL - deletes data)
   docker compose -f docker-compose.mcp-pro.yml down -v
   
   # Clean up Docker system
   docker system prune -f
   
   # Rebuild and restart
   docker compose -f docker-compose.mcp-pro.yml build --no-cache
   docker compose -f docker-compose.mcp-pro.yml up -d
   ```

2. **Individual Service Recovery**:
   ```bash
   # Reset specific service
   docker compose -f docker-compose.mcp-pro.yml stop docling-mcp
   docker compose -f docker-compose.mcp-pro.yml rm docling-mcp
   docker compose -f docker-compose.mcp-pro.yml build docling-mcp
   docker compose -f docker-compose.mcp-pro.yml up -d docling-mcp
   ```

3. **Configuration Recovery**:
   ```bash
   # Reset to default configuration
   docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 \
     python docling_mcp_server.py --create-config
   
   # Restart with default config
   docker compose -f docker-compose.mcp-pro.yml restart docling-mcp
   ```

## Preventive Measures

### Configuration Best Practices

1. **Use Environment-Specific Configurations**:
   ```yaml
   # development.yaml
   logging:
     level: DEBUG
   performance:
     tool_timeout: 60.0
   
   # production.yaml
   logging:
     level: WARNING
   performance:
     tool_timeout: 30.0
   ```

2. **Validate Configuration**:
   ```bash
   # Test configuration before deployment
   docker run --rm -v $(pwd)/config:/srv/config:ro \
     docling-mcp python -c "
from config import load_config
try:
    config = load_config()
    print('Configuration is valid')
except Exception as e:
    print(f'Configuration error: {e}')
    exit(1)
"
   ```

3. **Document Configuration Changes**:
   ```bash
   # Track configuration changes
   git add config/
   git commit -m "Update configuration for production deployment"
   git tag -a "v1.0.0-config" -m "Production configuration v1.0.0"
   ```

### Monitoring Setup Recommendations

1. **Enable Comprehensive Metrics**:
   ```yaml
   metrics:
     enabled: true
     collection_interval: 10.0
     retention_hours: 168  # 7 days
     storage_backend: "file"
     prometheus_enabled: true
     dashboard_enabled: true
     alerting_enabled: true
   ```

2. **Configure Alert Thresholds**:
   ```yaml
   metrics:
     alert_thresholds:
       cpu_usage_percent:
         warning: 70.0
         critical: 85.0
       memory_usage_percent:
         warning: 80.0
         critical: 90.0
       response_time_p95:
         warning: 1000.0
         critical: 2000.0
       error_rate:
         warning: 5.0
         critical: 10.0
   ```

3. **Set Up Log Aggregation**:
   ```yaml
   logging:
     level: INFO
     output: "/var/log/docling-mcp.log"
     format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
   ```

### Performance Optimization Guidelines

1. **Optimize Resource Usage**:
   ```yaml
   performance:
     tool_timeout: 30.0
     max_connections: 100
     rate_limit_requests: 1000
     rate_limit_window: 3600
   ```

2. **Enable Caching**:
   ```yaml
   docling:
     enable_cache: true
     cache_dir: "/data/cache"
     max_file_size: 104857600  # 100MB
   ```

3. **Configure Proper Timeouts**:
   ```yaml
   sse:
     connection_timeout: 30.0
     keepalive_interval: 0.1
   
   health_check:
     interval: 30
     timeout: 10
     retries: 3
     start_period: 30
   ```

### Security Hardening Procedures

1. **Configure CORS Properly**:
   ```yaml
   security:
     enable_cors: true
     allowed_origins: ["https://yourdomain.com"]
     enable_rate_limiting: true
     max_request_size: 10485760  # 10MB
   ```

2. **Enable Rate Limiting**:
   ```yaml
   performance:
     rate_limit_requests: 1000
     rate_limit_window: 3600
   ```

3. **Use Secure Transport**:
   ```yaml
   server:
     host: "0.0.0.0"
     port: 3020
     transport: "http"  # Use HTTPS in production
   ```

### Regular Maintenance Tasks

1. **Log Rotation**:
   ```bash
   # Set up log rotation
   sudo tee /etc/logrotate.d/docling-mcp << EOF
   /var/log/docling-mcp.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
       create 644 root root
   }
   EOF
   ```

2. **Cache Cleanup**:
   ```bash
   # Create cleanup script
   cat > cleanup_cache.sh << 'EOF'
   #!/bin/bash
   # Clean up old cache files
   find /data/cache -type f -mtime +7 -delete
   find /data/metrics -type f -mtime +30 -delete
   EOF
   
   chmod +x cleanup_cache.sh
   
   # Add to crontab
   echo "0 2 * * * /path/to/cleanup_cache.sh" | crontab -
   ```

3. **Health Monitoring**:
   ```bash
   # Create health monitoring script
   cat > health_monitor.sh << 'EOF'
   #!/bin/bash
   # Monitor service health
   if ! curl -f http://localhost:3020/health > /dev/null 2>&1; then
       echo "Docling MCP service is unhealthy" | mail -s "Service Alert" admin@example.com
       docker compose -f docker-compose.mcp-pro.yml restart docling-mcp
   fi
   EOF
   
   chmod +x health_monitor.sh
   
   # Add to crontab
   echo "*/5 * * * * /path/to/health_monitor.sh" | crontab -
   ```

## Troubleshooting Scripts

### Diagnostic Script

Create a comprehensive diagnostic script:

```bash
#!/bin/bash
# docling_mcp_diagnostics.sh - Comprehensive diagnostic script

set -e

echo "=== Docling MCP Service Diagnostics ==="
echo "Date: $(date)"
echo "System: $(uname -a)"
echo "Docker Version: $(docker --version)"
echo ""

echo "=== Service Status ==="
docker compose -f docker-compose.mcp-pro.yml ps
echo ""

echo "=== Recent Logs (last 50 lines) ==="
for service in docling-mcp mcp-gateway; do
    echo "--- $service ---"
    docker logs pmoves_multi_agent_pro_pack-${service}-1 --tail 50 | grep -i error || echo "No recent errors"
done
echo ""

echo "=== Network Connectivity ==="
echo "Testing docling-mcp endpoint:"
curl -v -H "Accept: text/event-stream" http://localhost:3020/mcp 2>&1 | head -20
echo ""
echo "Testing mcp-gateway endpoint:"
curl -v http://localhost:2091/health 2>&1 | head -20
echo ""

echo "=== Container Resource Usage ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo ""

echo "=== Configuration Check ==="
echo "Environment variables:"
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 env | grep DOCLING_MCP | sort
echo ""

echo "=== Volume Mounts ==="
docker inspect pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -A 20 Mounts
echo ""

echo "=== Health Check Status ==="
curl -f http://localhost:3020/health > /dev/null 2>&1 && echo "Docling-MCP: OK" || echo "Docling-MCP: FAILED"
curl -f http://localhost:2091/health > /dev/null 2>&1 && echo "MCP-Gateway: OK" || echo "MCP-Gateway: FAILED"
echo ""

echo "=== Port Availability ==="
netstat -an | grep -E "3020|2091" || echo "No ports found"
echo ""

echo "=== Disk Usage ==="
df -h | grep -E "/$|/data"
echo ""

echo "=== Memory Usage ==="
free -h
echo ""

echo "=== Docker System Info ==="
docker system df
echo ""

echo "=== Diagnostics Complete ==="
```

### Health Check Script

Create a health monitoring script:

```bash
#!/bin/bash
# health_check.sh - Service health monitoring script

set -e

SERVICES=("docling-mcp" "mcp-gateway")
ENDPOINTS=("http://localhost:3020/health" "http://localhost:2091/health")
LOG_FILE="/var/log/docling-mcp-health.log"

# Create log file if it doesn't exist
touch "$LOG_FILE"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check service health
check_service() {
    local service=$1
    local endpoint=$2
    
    if curl -f "$endpoint" > /dev/null 2>&1; then
        log_message "$service: HEALTHY"
        return 0
    else
        log_message "$service: UNHEALTHY"
        return 1
    fi
}

# Check all services
for i in "${!SERVICES[@]}"; do
    service="${SERVICES[$i]}"
    endpoint="${ENDPOINTS[$i]}"
    
    if ! check_service "$service" "$endpoint"; then
        log_message "Restarting $service..."
        docker compose -f docker-compose.mcp-pro.yml restart "$service"
        
        # Wait for service to start
        sleep 30
        
        # Check again
        if check_service "$service" "$endpoint"; then
            log_message "$service: RECOVERED"
        else
            log_message "$service: FAILED TO RECOVER - Manual intervention required"
        fi
    fi
done
```

### Performance Monitoring Script

Create a performance monitoring script:

```bash
#!/bin/bash
# performance_monitor.sh - Performance monitoring script

set -e

METRICS_FILE="/var/log/docling-mcp-metrics.log"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=80
ALERT_THRESHOLD_RESPONSE_TIME=2000

# Create metrics file if it doesn't exist
touch "$METRICS_FILE"

# Function to log metrics
log_metrics() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" pmoves_multi_agent_pro_pack-docling-mcp-1 | sed 's/%//')
    local memory_usage=$(docker stats --no-stream --format "{{.MemPerc}}" pmoves_multi_agent_pro_pack-docling-mcp-1 | sed 's/%//')
    local response_time=$(curl -o /dev/null -s -w "%{time_total}" http://localhost:3020/health)
    
    echo "$timestamp,$cpu_usage,$memory_usage,$response_time" >> "$METRICS_FILE"
    
    # Check thresholds
    if (( $(echo "$cpu_usage > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ALERT: High CPU usage: $cpu_usage%" >> "$METRICS_FILE"
    fi
    
    if (( $(echo "$memory_usage > $ALERT_THRESHOLD_MEMORY" | bc -l) )); then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ALERT: High memory usage: $memory_usage%" >> "$METRICS_FILE"
    fi
    
    if (( $(echo "$response_time > $ALERT_THRESHOLD_RESPONSE_TIME" | bc -l) )); then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ALERT: High response time: ${response_time}ms" >> "$METRICS_FILE"
    fi
}

# Monitor continuously
while true; do
    log_metrics
    sleep 60  # Collect metrics every minute
done
```

### Configuration Validation Script

Create a configuration validation script:

```bash
#!/bin/bash
# config_validator.sh - Configuration validation script

set -e

CONFIG_FILE="${1:-/srv/config/default.yaml}"
ERRORS=0

# Function to report errors
report_error() {
    echo "ERROR: $1"
    ERRORS=$((ERRORS + 1))
}

# Function to report warnings
report_warning() {
    echo "WARNING: $1"
}

echo "=== Configuration Validation ==="
echo "Checking configuration file: $CONFIG_FILE"
echo ""

# Check if configuration file exists
if [ ! -f "$CONFIG_FILE" ]; then
    report_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Validate YAML syntax
if ! python -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))" 2>/dev/null; then
    report_error "Invalid YAML syntax in configuration file"
fi

# Check required sections
if ! grep -q "server:" "$CONFIG_FILE"; then
    report_error "Missing 'server' section in configuration"
fi

if ! grep -q "logging:" "$CONFIG_FILE"; then
    report_error "Missing 'logging' section in configuration"
fi

# Validate server configuration
if grep -q "port:" "$CONFIG_FILE"; then
    port=$(grep "port:" "$CONFIG_FILE" | awk '{print $2}')
    if ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
        report_error "Invalid port number: $port (must be 1-65535)"
    fi
fi

# Validate logging configuration
if grep -q "level:" "$CONFIG_FILE"; then
    level=$(grep "level:" "$CONFIG_FILE" | awk '{print $2}' | tr -d '"')
    case "$level" in
        DEBUG|INFO|WARNING|ERROR)
            # Valid log level
            ;;
        *)
            report_error "Invalid log level: $level (must be DEBUG, INFO, WARNING, or ERROR)"
            ;;
    esac
fi

# Check security settings
if grep -q "enable_cors: true" "$CONFIG_FILE"; then
    if grep -q "allowed_origins:" "$CONFIG_FILE"; then
        origins=$(grep -A 5 "allowed_origins:" "$CONFIG_FILE" | grep -E '^\s*-' | wc -l)
        if [ "$origins" -eq 0 ]; then
            report_warning "CORS enabled but no allowed origins specified"
        fi
    fi
fi

# Check performance settings
if grep -q "tool_timeout:" "$CONFIG_FILE"; then
    timeout=$(grep "tool_timeout:" "$CONFIG_FILE" | awk '{print $2}')
    if ! [[ "$timeout" =~ ^[0-9]+\.?[0-9]*$ ]] || [ "$timeout" -le 0 ]; then
        report_error "Invalid tool timeout: $timeout (must be positive number)"
    fi
fi

# Report results
echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo "Configuration validation PASSED"
    exit 0
else
    echo "Configuration validation FAILED with $ERRORS error(s)"
    exit 1
fi
```

This comprehensive troubleshooting guide provides detailed procedures for diagnosing and resolving common issues with the docling-mcp service. Use the diagnostic scripts to automate troubleshooting and the preventive measures to maintain system health.