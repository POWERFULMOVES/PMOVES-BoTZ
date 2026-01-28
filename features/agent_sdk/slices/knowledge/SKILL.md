# Knowledge Management Skill

**Slice:** `slices/knowledge/`
**Type:** Knowledge Base Operations

## Purpose

Hi-RAG v2 knowledge base management. Use this skill when:
- Searching the knowledge base for information
- Ingesting new documents into the knowledge base
- Managing knowledge index health

## Quick Start

```python
from slices.knowledge import KnowledgeService, KnowledgeTask, RetrievalMode

service = KnowledgeService(http_client=client)

# Query knowledge
task = KnowledgeTask(
    query="How does TensorZero routing work?",
    retrieval_mode=RetrievalMode.HYBRID,
    top_k=10,
    rerank=True,
)
result = await service.execute(task)

for chunk in result.chunks:
    print(f"[{chunk.score:.2f}] {chunk.content[:100]}")
```

## API Reference

### KnowledgeService

| Method | Description | Returns |
|--------|-------------|---------|
| `execute(task)` | Execute knowledge task | `KnowledgeResult` |
| `health_check()` | Check service health | `Dict[str, bool]` |

### Retrieval Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| VECTOR | Qdrant semantic search | Conceptual similarity |
| GRAPH | Neo4j knowledge graph | Entity relationships |
| FULLTEXT | Meilisearch text search | Exact phrase matching |
| HYBRID | All three combined | Best overall relevance |

### Index Operations

| Operation | Description | Requires |
|-----------|-------------|----------|
| INGEST | Add new documents | documents list |
| UPDATE | Update existing | documents with ids |
| DELETE | Remove documents | filters or ids |
| REINDEX | Full reindex | none |

## Integration Points

| Service | URL | Purpose |
|---------|-----|---------|
| Hi-RAG v2 | localhost:8086 | Hybrid retrieval |
| Qdrant | localhost:6333 | Vector store |
| Neo4j | localhost:7474 | Knowledge graph |
| Meilisearch | localhost:7700 | Full-text search |

## Example: Document Ingestion

```python
from slices.knowledge import KnowledgeTask, IndexOperation

# Ingest new documents
task = KnowledgeTask(
    operation=IndexOperation.INGEST,
    documents=[
        {
            "content": "TensorZero is a unified LLM gateway...",
            "source": "docs/tensorzero.md",
            "metadata": {"type": "documentation"},
        }
    ],
)
result = await service.execute(task)
print(f"Processed {result.documents_processed} documents")
```

## Retrieval Strategy

1. **Hybrid Mode** (Default): Combines all three retrieval methods
2. **Cross-encoder Reranking**: Improves relevance with neural reranker
3. **Filtering**: Apply metadata filters to narrow results
4. **Top-K**: Control number of results returned

## Best Practices

- Use HYBRID mode for general queries
- Use VECTOR for conceptual/semantic search
- Use FULLTEXT for exact phrase matching
- Use GRAPH for entity relationship queries
- Always enable reranking for best relevance
