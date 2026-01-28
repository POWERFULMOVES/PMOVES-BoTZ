"""
Knowledge Slice - Data Models.

Defines data structures for Hi-RAG knowledge management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class RetrievalMode(Enum):
    """Retrieval modes for knowledge queries."""
    VECTOR = "vector"          # Qdrant semantic search
    GRAPH = "graph"            # Neo4j knowledge graph
    FULLTEXT = "fulltext"      # Meilisearch
    HYBRID = "hybrid"          # All three combined


class IndexOperation(Enum):
    """Index operations for knowledge management."""
    INGEST = "ingest"          # Add new documents
    UPDATE = "update"          # Update existing
    DELETE = "delete"          # Remove documents
    REINDEX = "reindex"        # Full reindex


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge from the knowledge base."""
    id: str
    content: str
    source: str
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass
class KnowledgeTask:
    """A knowledge management task specification."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: IndexOperation = IndexOperation.INGEST
    query: Optional[str] = None  # For retrieval operations
    documents: List[Dict] = field(default_factory=list)  # For ingest operations
    retrieval_mode: RetrievalMode = RetrievalMode.HYBRID
    top_k: int = 10
    rerank: bool = True
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "operation": self.operation.value,
            "query": self.query,
            "documents": self.documents,
            "retrieval_mode": self.retrieval_mode.value,
            "top_k": self.top_k,
            "rerank": self.rerank,
            "filters": self.filters,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class KnowledgeResult:
    """Result of a knowledge management task."""
    task_id: str
    chunks: List[KnowledgeChunk] = field(default_factory=list)
    documents_processed: int = 0
    total_found: int = 0
    retrieval_mode_used: RetrievalMode = RetrievalMode.HYBRID
    completed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    duration_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "chunks": [c.to_dict() for c in self.chunks],
            "documents_processed": self.documents_processed,
            "total_found": self.total_found,
            "retrieval_mode_used": self.retrieval_mode_used.value,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }
