# Cipher Recall Memory

Recall memories from the Cipher dual-layer memory system.

## Arguments

- `$ARGUMENTS` - Query to search for in memory (semantic search)

## Instructions

1. Call Cipher Memory MCP tool `recall_memory`
2. Search across both System 1 (concepts) and System 2 (reasoning) layers
3. Return relevant memories with relevance scores

```bash
# Recall memory via MCP STDIO
docker exec -i pmz-cipher python3 memory_shim/app_cipher_memory.py << 'EOF'
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "recall_memory",
    "arguments": {
      "query": "$ARGUMENTS",
      "top_k": 5
    }
  },
  "id": 1
}
EOF
```

## Search Parameters

- `query`: Natural language search query
- `top_k`: Number of results to return (default: 5)
- `layer`: Optional - filter to specific layer ("system1" or "system2")

## Examples

```
/cipher:recall PMOVES architecture
/cipher:recall deployment patterns
/cipher:recall previous coding decisions
```

Report:
- Matching memories with content
- Relevance scores
- Memory IDs
- Which layer each memory came from
