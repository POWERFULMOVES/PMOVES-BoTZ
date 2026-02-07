"""
Research Slice - Data Models.

Defines the data structures for research tasks and results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class SourceType(Enum):
    """Types of research sources."""
    HIRAG = "hirag"
    WEB_SEARCH = "web_search"
    SUPASERCH = "supaserch"
    DEEP_RESEARCH = "deep_research"
    DOCUMENT = "document"
    UNKNOWN = "unknown"  # Fallback for unrecognized source types

    @classmethod
    def _missing_(cls, value: object) -> "SourceType":  # noqa: ARG003
        """Handle unknown source type values gracefully."""
        return cls.UNKNOWN


class ConfidenceLevel(Enum):
    """Confidence levels for research findings."""
    HIGH = "high"          # Multiple corroborating sources
    MEDIUM = "medium"      # Single authoritative source
    LOW = "low"            # Extrapolation or inference
    UNCERTAIN = "uncertain"


class ResearchDepth(Enum):
    """Depth levels for research tasks."""
    SHALLOW = "shallow"    # Quick lookup, limited sources
    STANDARD = "standard"  # Normal research, balanced depth
    DEEP = "deep"          # Comprehensive research, all sources


@dataclass
class SourceCitation:
    """Citation for a research source."""
    type: SourceType
    title: str
    url: Optional[str] = None
    excerpt: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "title": self.title,
            "url": self.url,
            "excerpt": self.excerpt,
            "retrieved_at": self.retrieved_at,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
        }


@dataclass
class ResearchTask:
    """A research task specification."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    depth: ResearchDepth = ResearchDepth.STANDARD
    sources: List[SourceType] = field(default_factory=lambda: [SourceType.HIRAG, SourceType.WEB_SEARCH])
    max_sources: int = 10
    include_citations: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "query": self.query,
            "depth": self.depth.value,
            "sources": [s.value for s in self.sources],
            "max_sources": self.max_sources,
            "include_citations": self.include_citations,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class ResearchResult:
    """Result of a research task."""
    task_id: str
    summary: str
    findings: List[str] = field(default_factory=list)
    citations: List[SourceCitation] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    completed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "summary": self.summary,
            "findings": self.findings,
            "citations": [c.to_dict() for c in self.citations],
            "confidence": self.confidence.value,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }
