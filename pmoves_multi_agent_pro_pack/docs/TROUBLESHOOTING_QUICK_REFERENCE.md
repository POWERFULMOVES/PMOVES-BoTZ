# Troubleshooting Quick Reference Guide

This guide provides quick reference for common docling-mcp service issues with immediate solutions and links to detailed troubleshooting procedures.

## Quick Diagnostic Commands

### Service Status
```bash
# Check all services
docker compose -f docker-compose.mcp-pro.yml ps

# Check service health
curl http://localhost:3020/health
curl http://localhost:2091/health

# View recent logs
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 --tail 20
```

### Network Tests
```bash
# Test SSE endpoint
curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp

# Test gateway
curl http://localhost:2091/health

# Test service connectivity
docker exec -it pmoves_multi_agent_pro_pack-mcp-gateway-1 curl http://docling-mcp:3020/mcp
```

## Common Issues & Quick Fixes

### Service Won't Start
**Quick Fix:**
```bash
# Restart services
docker compose -f docker-compose.mcp-pro.yml restart

# Check logs for errors
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -i error
```

**Detailed Solution:** See [Service Startup Errors](TROUBLESHOOTING.md#deployment-issues)

### SSE Connection Failures
**Quick Fix:**
```bash
# Check CORS headers
curl -I -X OPTIONS http://localhost:3020/mcp

# Test with proper headers
curl -N -H "Accept: text/event-stream" -H "Cache-Control: no-cache" http://localhost:3020/mcp
```

**Detailed Solution:** See [SSE Connection Failures](TROUBLESHOOTING.md#sse-connection-failures)

### Performance Issues
**Quick Fix:**
```bash
# Check resource usage
docker stats pmoves_multi_agent_pro_pack-docling-mcp-1

# Monitor response times
time curl http://localhost:3020/health
```

**Detailed Solution:** See [Performance Issues](TROUBLESHOOTING.md#performance-issues)

### Configuration Problems
**Quick Fix:**
```bash
# Validate configuration
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "
from config import load_config
try:
    config = load_config()
    print('Configuration valid')
except Exception as e:
    print(f'Error: {e}')
"

# Check environment variables
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 env | grep DOCLING_MCP
```

**Detailed Solution:** See [Configuration Problems](TROUBLESHOOTING.md#configuration-problems)

### Document Processing Errors
**Quick Fix:**
```bash
# Check Docling installation
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 python -c "
try:
    from docling.document_converter import DocumentConverter
    print('Docling available')
except ImportError as e:
    print(f'Docling error: {e}')
"

# Check file permissions
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 ls -la /data/
```

**Detailed Solution:** See [Document Processing Issues](TROUBLESHOOTING.md#document-processing-issues)

### Health Check Failures
**Quick Fix:**
```bash
# Test health endpoint manually
curl -v http://localhost:3020/health

# Check health check configuration
docker inspect pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -A 10 Health
```

**Detailed Solution:** See [Health Check Problems](TROUBLESHOOTING.md#health-check-problems)

## Emergency Procedures

### Complete Service Reset
```bash
# Stop all services
docker compose -f docker-compose.mcp-pro.yml down

# Clean up (removes data - be careful)
docker compose -f docker-compose.mcp-pro.yml down -v

# Rebuild and restart
docker compose -f docker-compose.mcp-pro.yml build --no-cache
docker compose -f docker-compose.mcp-pro.yml up -d
```

### Individual Service Recovery
```bash
# Restart specific service
docker compose -f docker-compose.mcp-pro.yml restart docling-mcp

# Rebuild specific service
docker compose -f docker-compose.mcp-pro.yml stop docling-mcp
docker compose -f docker-compose.mcp-pro.yml rm docling-mcp
docker compose -f docker-compose.mcp-pro.yml build docling-mcp
docker compose -f docker-compose.mcp-pro.yml up -d docling-mcp
```

## Script References

### Automated Diagnostics
```bash
# Run comprehensive diagnostics
./scripts/docling_mcp_diagnostics.sh

# Run health monitoring
./scripts/health_check.sh

# Monitor performance
./scripts/performance_monitor.sh &

# Validate configuration
./scripts/config_validator.sh

# Analyze logs
./scripts/log_analyzer.sh /var/log/docling-mcp.log errors
```

**Script Location:** See [Troubleshooting Scripts](TROUBLESHOOTING_SCRIPTS.md)

## Configuration Quick Fixes

### Common Environment Variables
```bash
# Fix transport type
export DOCLING_MCP_SERVER__TRANSPORT=http

# Fix logging level
export DOCLING_MCP_LOGGING__LEVEL=DEBUG

# Fix timeouts
export DOCLING_MCP_PERFORMANCE__TOOL_TIMEOUT=60.0

# Fix CORS
export DOCLING_MCP_SECURITY__ENABLE_CORS=true
export DOCLING_MCP_SECURITY__ALLOWED_ORIGINS="*"
```

### Docker Compose Quick Fixes
```yaml
# Common fixes in docker-compose.mcp-pro.yml
services:
  docling-mcp:
    environment:
      DOCLING_MCP_SERVER__HOST: 0.0.0.0
      DOCLING_MCP_SERVER__PORT: 3020
      DOCLING_MCP_LOGGING__LEVEL: INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3020/health"]
      interval: 30s
      timeout: 15s
      retries: 5
      start_period: 60s
```

## Performance Quick Fixes

### Resource Limits
```yaml
# In configuration file
performance:
  tool_timeout: 60.0
  max_connections: 100
  rate_limit_requests: 1000
  rate_limit_window: 3600

metrics:
  enabled: true
  collection_interval: 30.0  # Reduce overhead
  retention_hours: 24
```

### Memory Optimization
```bash
# Clear cache
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 rm -rf /data/cache/*

# Restart service
docker compose -f docker-compose.mcp-pro.yml restart docling-mcp
```

## Security Quick Fixes

### CORS Issues
```yaml
# In configuration file
security:
  enable_cors: true
  allowed_origins: ["http://localhost:3000", "https://yourdomain.com"]

sse:
  cors_origins: ["http://localhost:3000", "https://yourdomain.com"]
  cors_methods: ["GET", "OPTIONS"]
  cors_headers: ["Content-Type", "Accept", "Cache-Control"]
```

### Rate Limiting
```yaml
# In configuration file
performance:
  rate_limit_requests: 1000
  rate_limit_window: 3600

security:
  enable_rate_limiting: true
  max_request_size: 10485760  # 10MB
```

## Monitoring Quick Setup

### Basic Metrics
```bash
# Enable metrics endpoint
curl http://localhost:3020/metrics

# Check dashboard
open http://localhost:3020/dashboard
```

### Log Monitoring
```bash
# Follow logs in real-time
docker logs -f pmoves_multi_agent_pro_pack-docling-mcp-1

# Filter for errors
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -i error
```

## Getting Help

### Information to Collect
When reporting issues, provide:

1. **Service Status**: `docker compose -f docker-compose.mcp-pro.yml ps`
2. **Error Logs**: `docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 --tail 50`
3. **Configuration**: Your `config/default.yaml` or environment variables
4. **System Info**: Docker version, OS, available resources
5. **Reproduction Steps**: Exact commands that led to the issue

### Debug Information Collection
```bash
# Create debug bundle
mkdir -p debug_bundle
docker logs pmoves_multi_agent_pro_pack-docling-mcp-1 > debug_bundle/docling-mcp.log
docker compose -f docker-compose.mcp-pro.yml config > debug_bundle/docker-compose.yml
docker inspect pmoves_multi_agent_pro_pack-docling-mcp-1 > debug_bundle/container-inspect.json
tar -czf debug_bundle.tar.gz debug_bundle/
```

### Contact Information
- **Documentation**: See [Troubleshooting Guide](TROUBLESHOOTING.md)
- **Scripts**: See [Troubleshooting Scripts](TROUBLESHOOTING_SCRIPTS.md)
- **Configuration**: See [Configuration Guide](CONFIGURATION_GUIDE.md)
- **Performance**: See [Performance Monitoring](PERFORMANCE_MONITORING.md)
- **Testing**: See [Test Documentation](../tests/README.md)

## Quick Reference Summary

| Issue | Quick Fix | Detailed Solution |
|--------|------------|------------------|
| Service won't start | `docker compose restart` | [Service Startup Errors](TROUBLESHOOTING.md#deployment-issues) |
| SSE connection fails | Check CORS headers | [SSE Connection Failures](TROUBLESHOOTING.md#sse-connection-failures) |
| Performance slow | Check `docker stats` | [Performance Issues](TROUBLESHOOTING.md#performance-issues) |
| Configuration errors | Validate with script | [Configuration Problems](TROUBLESHOOTING.md#configuration-problems) |
| Document processing fails | Check Docling import | [Document Processing Issues](TROUBLESHOOTING.md#document-processing-issues) |
| Health check fails | Test endpoint manually | [Health Check Problems](TROUBLESHOOTING.md#health-check-problems) |
| Need diagnostics | Run diagnostic script | [Diagnostic Tools](TROUBLESHOOTING_SCRIPTS.md) |

This quick reference guide provides immediate solutions for common issues. For detailed troubleshooting procedures, refer to the comprehensive guides linked above.