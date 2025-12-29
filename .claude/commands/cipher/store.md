# Cipher Store Memory

Store a memory item in the Cipher dual-layer memory system.

## Arguments

- `$ARGUMENTS` - Key and content to store (format: "key: content" or just content)

## Instructions

1. Parse key and content from arguments
2. Call Cipher Memory MCP tool `store_memory`
3. Report storage confirmation and memory ID

```bash
# Store memory via MCP STDIO
docker exec -i pmz-cipher python3 memory_shim/app_cipher_memory.py << 'EOF'
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "store_memory",
    "arguments": {
      "key": "$KEY",
      "content": "$CONTENT",
      "layer": "system1"
    }
  },
  "id": 1
}
EOF
```

## Memory Layers

- **System 1 (Concepts)**: Fast associative memory for patterns and facts
- **System 2 (Reasoning)**: Deliberate reasoning chains and complex analysis

## Examples

```
/cipher:store project_context: PMOVES.AI is a multi-agent orchestration platform
/cipher:store The deployment uses TensorZero for model routing
```

Report:
- Memory ID assigned
- Layer stored to (System 1 or System 2)
- Confirmation of storage
