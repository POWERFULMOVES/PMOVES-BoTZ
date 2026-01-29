"""
Research Slice - Deep Research via Hi-RAG, SupaSerch, and Web Search.

This vertical slice encapsulates all research functionality:
- api.py: Research task endpoints
- service.py: Research orchestration logic
- models.py: Research data structures
- SKILL.md: Agent context for research tasks

Use: from slices.research import ResearchService
"""

from .models import (
    ConfidenceLevel,
    ResearchDepth,
    ResearchResult,
    ResearchTask,
    SourceCitation,
    SourceType,
)
from .service import ResearchService
from .. import register_slice

# Register this slice
register_slice("research")(ResearchService)

__all__ = [
    "ConfidenceLevel",
    "ResearchDepth",
    "ResearchResult",
    "ResearchService",
    "ResearchTask",
    "SourceCitation",
    "SourceType",
]
