# Cipher Status

Check Cipher Memory service health and statistics.

## Instructions

1. Check Cipher container status
2. Get memory statistics (count, layers)
3. Verify LLM provider connection

```bash
# Check container status
docker ps --filter "name=pmz-cipher" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check Cipher config
docker exec pmz-cipher cat /app/memAgent/cipher_pmoves.yml 2>/dev/null | head -30

# Get memory stats via MCP
docker exec -i pmz-cipher python3 memory_shim/app_cipher_memory.py << 'EOF'
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_stats",
    "arguments": {}
  },
  "id": 1
}
EOF
```

## Configuration

Cipher uses these environment variables:
- `VENICE_API_KEY`: LLM provider for reasoning
- `CIPHER_CONFIG_PATH`: Custom config path

## Health Indicators

- Container running
- Config file accessible
- LLM provider responding
- Memory storage accessible

Report:
- Container status
- Memory counts per layer
- LLM provider configuration
- Any errors or warnings
