# Research Skill

**Slice:** `slices/research/`
**Type:** Knowledge Retrieval & Synthesis

## Purpose

Deep research via Hi-RAG, SupaSerch, and web search. Use this skill when:
- The user needs comprehensive information on a topic
- Multiple sources need to be consulted and synthesized
- Citations and confidence levels are required

## Quick Start

```python
from slices.research import ResearchService, ResearchTask, SourceType

service = ResearchService(http_client=client)
task = ResearchTask(
    query="How does TensorZero routing work?",
    sources=[SourceType.HIRAG, SourceType.WEB_SEARCH],
    depth="deep",
)
result = await service.execute(task)
print(result.summary)
```

## API Reference

### ResearchService

| Method | Description | Returns |
|--------|-------------|---------|
| `execute(task)` | Execute a research task | `ResearchResult` |

### ResearchTask

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | str | "" | Research question |
| `depth` | str | "standard" | shallow, standard, deep |
| `sources` | List[SourceType] | [HIRAG, WEB_SEARCH] | Sources to query |
| `max_sources` | int | 10 | Maximum sources to include |

### ConfidenceLevel

- **HIGH**: Multiple corroborating sources (3+ high-quality)
- **MEDIUM**: Single authoritative or 3+ sources
- **LOW**: Limited sources
- **UNCERTAIN**: No sources found

## Integration Points

- **Hi-RAG v2**: `http://localhost:8086/hirag/query`
- **TensorZero**: `http://localhost:3030/v1/chat/completions`
- **NATS Events**: `botz.research.completed.v1`

## Example Workflow

1. Create research task with query
2. Service queries Hi-RAG and web sources in parallel
3. Results are ranked by relevance
4. Findings are synthesized with confidence levels
5. Citations are included for verification
