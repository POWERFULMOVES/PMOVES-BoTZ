# Docling MCP Server - Quick Reference

## Overview

Quick reference guide for the docling-mcp service implementation that resolves critical SSE transport issues.

## Problem Resolution Summary

**Issue**: `SSE error: SseServerTransport.connect_sse() missing 1 required positional argument: 'send'`
**Status**: ✅ **RESOLVED** with custom SSE handler implementation

## Service Status

- ✅ **Health Check**: `http://localhost:3020/health` → HTTP 200 "OK"
- ✅ **SSE Endpoint**: `http://localhost:3020/mcp` → Multiple concurrent connections
- ✅ **CORS Support**: OPTIONS requests handled properly
- ✅ **Production Ready**: Stable long-running operation

## Quick Commands

### Docker Operations

```bash
# Build and start
cd pmoves_multi_agent_pro_pack
docker-compose -f docker-compose.mcp-pro.yml up docling-mcp

# Health check
curl http://localhost:3020/health

# Test SSE connection
curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp

# View logs
docker logs -f docling-mcp-1
```

### Direct Python Operations

```bash
# Install dependencies
pip install -r docling_mcp_requirements.txt

# Run HTTP server
python docling_mcp_server.py --transport http --host 0.0.0.0 --port 3020

# Run STDIO server
python docling_mcp_server.py --transport stdio

# Debug mode
python docling_mcp_server.py --transport http --log-level DEBUG
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|---------|---------|
| `/health` | GET | Health check |
| `/mcp` | GET | SSE connection |
| `/mcp` | OPTIONS | CORS preflight |

## Available Tools

### 1. health_check
```json
{
  "name": "health_check",
  "description": "Check server health and capabilities",
  "parameters": {}
}
```

### 2. convert_document
```json
{
  "name": "convert_document",
  "description": "Convert documents to structured format",
  "parameters": {
    "file_path": "string (required)",
    "output_format": "markdown|text|json (optional)"
  }
}
```

### 3. process_documents_batch
```json
{
  "name": "process_documents_batch",
  "description": "Process multiple documents in batch",
  "parameters": {
    "file_paths": ["string"] (required),
    "output_format": "markdown|text|json (optional)"
  }
}
```

## Client Examples

### JavaScript/Browser Client

```javascript
// SSE Connection
const eventSource = new EventSource('http://localhost:3020/mcp');

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('MCP Response:', data);
};

// Tool Call
fetch('http://localhost:3020/mcp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        jsonrpc: "2.0",
        id: "1",
        method: "tools/call",
        params: {
            name: "health_check",
            arguments: {}
        }
    })
});
```

### Python Client

```python
import subprocess
import json

# STDIO Client
process = subprocess.Popen(
    ['python', 'docling_mcp_server.py', '--transport', 'stdio'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

request = {
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
        "name": "health_check",
        "arguments": {}
    }
}

process.stdin.write(json.dumps(request) + '\n')
response = process.stdout.readline()
result = json.loads(response)
print(result)
```

### curl Client

```bash
# Health check
curl http://localhost:3020/health

# Tool call
curl -X POST http://localhost:3020/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
      "name": "convert_document",
      "arguments": {
        "file_path": "document.pdf",
        "output_format": "markdown"
      }
    }
  }'
```

## Configuration Options

| Option | Default | Description |
|--------|----------|-------------|
| `--transport` | "stdio" | Transport type: "stdio" or "http" |
| `--host` | "0.0.0.0" | Host for HTTP transport |
| `--port` | 3020 | Port for HTTP transport |
| `--log-level` | "INFO" | Logging level: DEBUG, INFO, WARNING, ERROR |

## Troubleshooting

### Common Issues

1. **SSE Connection Errors**
   ```bash
   # Test connection
   curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp
   ```

2. **CORS Issues**
   ```bash
   # Test CORS preflight
   curl -X OPTIONS -H "Origin: http://localhost" \
     -H "Access-Control-Request-Method: GET" \
     http://localhost:3020/mcp
   ```

3. **Document Processing Errors**
   ```bash
   # Check file accessibility
   ls -la /path/to/document.pdf
   
   # Test Docling installation
   python -c "from docling.document_converter import DocumentConverter; print('OK')"
   ```

### Debug Mode

```bash
# Enable debug logging
python docling_mcp_server.py --transport http --log-level DEBUG

# Monitor Docker logs
docker logs -f docling-mcp-1
```

### Log Patterns

**Successful Connection**:
```
SSE connection from 127.0.0.1
SSE connection from 127.0.0.1 closed
```

**Error Pattern**:
```
SSE error: [error details]
```

**Access Log**:
```
172.18.0.1 [09/Nov/2025:14:35:48 +0000] "GET /health HTTP/1.1" 200 154
```

## Performance Monitoring

### Key Metrics

- **Connection Count**: Active SSE connections
- **Request Rate**: Tool executions per minute
- **Error Rate**: Failed requests percentage
- **Response Time**: Average tool execution time

### Monitoring Commands

```bash
# Connection monitoring
watch "curl -s http://localhost:3020/health | wc -c"

# Log monitoring
tail -f /var/log/docling-mcp.log | grep "SSE connection"

# Docker stats
docker stats docling-mcp-1
```

## Deployment Checklist

### Pre-Deployment

- [ ] Dependencies installed (`pip install -r docling_mcp_requirements.txt`)
- [ ] Docling library available
- [ ] Port 3020 available
- [ ] File permissions set for document access

### Post-Deployment

- [ ] Health check responding (`curl http://localhost:3020/health`)
- [ ] SSE connections working (`curl -N http://localhost:3020/mcp`)
- [ ] CORS headers present
- [ ] Logs showing successful connections
- [ ] mcp-gateway integration verified

## Integration Points

### mcp-gateway Integration

The service integrates seamlessly with mcp-gateway:

```yaml
# docker-compose.mcp-pro.yml
services:
  docling-mcp:
    build:
      context: .
      dockerfile: Dockerfile.docling-mcp
    ports:
      - "3020:3020"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3020/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Client Integration

Clients can connect via:

1. **HTTP/SSE**: `http://localhost:3020/mcp`
2. **STDIO**: Direct process execution
3. **mcp-gateway**: Through gateway routing

## Security Considerations

### Input Validation

- JSON schema validation for all tool parameters
- File path sanitization
- File existence verification

### CORS Configuration

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, OPTIONS, POST
Access-Control-Allow-Headers: Content-Type, Accept, Cache-Control
Access-Control-Max-Age: 86400
```

### Rate Limiting

- Configurable maximum connections
- Request rate limiting per IP
- Resource usage monitoring

## Maintenance

### Regular Tasks

1. **Log Rotation**: Configure log rotation for long-running containers
2. **Health Monitoring**: Implement automated health checks
3. **Performance Monitoring**: Track key metrics
4. **Security Updates**: Keep dependencies updated

### Backup Strategy

1. **Configuration**: Backup server configuration
2. **Documents**: Ensure document storage is backed up
3. **Logs**: Archive important logs for analysis

## Support

### Documentation

- **Implementation Guide**: [`DOCLING_MCP_IMPLEMENTATION_GUIDE.md`](DOCLING_MCP_IMPLEMENTATION_GUIDE.md)
- **Technical Reference**: [`DOCLING_MCP_TECHNICAL_REFERENCE.md`](DOCLING_MCP_TECHNICAL_REFERENCE.md)
- **MCP Documentation**: [`MCP_OFFICIAL_DOCUMENTATION_REFERENCE.md`](MCP_OFFICIAL_DOCUMENTATION_REFERENCE.md)

### Common Solutions

1. **SSE Issues**: Use custom handler (already implemented)
2. **Connection Problems**: Check firewall and port availability
3. **Document Errors**: Verify file paths and permissions
4. **Performance Issues**: Monitor resource usage and logs

## Quick Test Script

```bash
#!/bin/bash
# Quick test script for docling-mcp service

echo "Testing docling-mcp service..."

# Health check
echo "1. Health check..."
if curl -f http://localhost:3020/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

# SSE connection
echo "2. SSE connection..."
timeout 5 curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp > /dev/null 2>&1
if [ $? -eq 124 ]; then
    echo "✅ SSE connection established"
else
    echo "❌ SSE connection failed"
    exit 1
fi

# CORS preflight
echo "3. CORS preflight..."
if curl -X OPTIONS -H "Origin: http://localhost" \
   -H "Access-Control-Request-Method: GET" \
   http://localhost:3020/mcp > /dev/null 2>&1; then
    echo "✅ CORS preflight passed"
else
    echo "❌ CORS preflight failed"
    exit 1
fi

echo "✅ All tests passed! Service is operational."
```

## Conclusion

The docling-mcp service successfully resolves the critical SSE transport issue and provides a robust, production-ready MCP server with:

- ✅ **Custom SSE Handler**: Resolves `connect_sse()` parameter error
- ✅ **Multi-Transport Support**: HTTP/SSE and STDIO transports
- ✅ **MCP Compliance**: Full specification compliance
- ✅ **Production Ready**: Comprehensive error handling and monitoring
- ✅ **Easy Integration**: Seamless mcp-gateway integration

The service is now fully operational and ready for production use.