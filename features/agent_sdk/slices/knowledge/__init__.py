"""
Knowledge Slice - Hi-RAG Knowledge Base Management.

This vertical slice encapsulates all knowledge management functionality:
- api.py: Knowledge task endpoints
- service.py: Retrieval and indexing logic
- models.py: Knowledge data structures
- SKILL.md: Agent context for knowledge tasks

Use: from slices.knowledge import KnowledgeService
"""

from .service import KnowledgeService
from .models import KnowledgeTask, KnowledgeResult, IndexOperation, RetrievalMode
from .. import register_slice

# Register this slice
register_slice("knowledge")(KnowledgeService)

__all__ = [
    "KnowledgeService",
    "KnowledgeTask",
    "KnowledgeResult",
    "IndexOperation",
    "RetrievalMode",
]
