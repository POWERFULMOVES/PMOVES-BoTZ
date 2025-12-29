# BoTZ Start

Start all PMOVES-BoTZ MCP services.

## Arguments

- `$ARGUMENTS` - Optional: specific service name (docling, e2b, cipher, vl-sentinel, postman, n8n-agent)

## Instructions

1. If specific service provided, start only that service
2. Otherwise start all BoTZ services via docker compose
3. Verify health endpoints after startup

```bash
# Start all services
cd /home/pmoves/PMOVES.AI/PMOVES-BoTZ
docker compose -f core/docker-compose/docker-compose.yml up -d

# Or start specific service
docker compose -f core/docker-compose/docker-compose.yml up -d $ARGUMENTS
```

After startup, verify health:
```bash
# Check Docling
curl -sf http://localhost:3020/health && echo "Docling: OK" || echo "Docling: FAILED"

# Check E2B
curl -sf http://localhost:7071/health && echo "E2B: OK" || echo "E2B: FAILED"

# Check VL Sentinel
curl -sf http://localhost:7072/health && echo "VL Sentinel: OK" || echo "VL Sentinel: FAILED"
```

Report:
- Services started
- Health check results
- Any startup errors from logs
