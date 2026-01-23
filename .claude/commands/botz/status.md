# BoTZ Status

Check health status of all PMOVES-BoTZ MCP services.

## Instructions

1. Check docker container status
2. Test health endpoints for all services
3. Report which services are healthy/unhealthy

```bash
# Check container status
docker ps --filter "name=pmz-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health checks
echo "=== Service Health ==="

# Docling MCP
curl -sf http://localhost:3020/health -o /dev/null && echo "Docling (3020): OK" || echo "Docling (3020): DOWN"

# E2B Sandbox
curl -sf http://localhost:7071/health -o /dev/null && echo "E2B (7071): OK" || echo "E2B (7071): DOWN"

# VL Sentinel
curl -sf http://localhost:7072/health -o /dev/null && echo "VL Sentinel (7072): OK" || echo "VL Sentinel (7072): DOWN"

# Cipher Memory (check container)
docker ps --filter "name=pmz-cipher" --format "{{.Status}}" | grep -q "Up" && echo "Cipher (8081): OK" || echo "Cipher (8081): DOWN"
```

Report:
- Container statuses (running, stopped, unhealthy)
- Health endpoint results
- Port mappings
- Any error logs (last 10 lines if unhealthy)
