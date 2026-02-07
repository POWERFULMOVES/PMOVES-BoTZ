"""
Research Slice - Service Layer.

Orchestrates research tasks across multiple sources:
- Hi-RAG v2 for semantic knowledge retrieval
- Web search for current information
- SupaSerch for multimodal research
- DeepResearch for LLM-based research planning
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .models import (
    ConfidenceLevel,
    ResearchResult,
    ResearchTask,
    SourceCitation,
    SourceType,
)

logger = logging.getLogger(__name__)


class ResearchService:
    """
    Research Service - Coordinates multi-source research tasks.

    This service encapsulates all research logic in a single vertical slice,
    making it easy for AI agents to understand and modify.

    Usage:
        service = ResearchService(http_client=client, hirag_url="http://localhost:8086")
        result = await service.execute(ResearchTask(query="How does TensorZero work?"))
    """

    def __init__(
        self,
        http_client: Optional[Any] = None,
        hirag_url: str = "http://localhost:8086",
        tensorzero_url: str = "http://localhost:3030",
    ):
        """
        Initialize Research Service.

        Args:
            http_client: Async HTTP client (e.g., httpx.AsyncClient)
            hirag_url: Hi-RAG v2 service URL
            tensorzero_url: TensorZero gateway URL
        """
        self.http_client = http_client
        self.hirag_url = hirag_url
        self.tensorzero_url = tensorzero_url

    async def execute(self, task: ResearchTask) -> ResearchResult:
        """
        Execute a research task.

        Args:
            task: Research task specification

        Returns:
            ResearchResult with findings and citations
        """
        start_time = time.time()
        citations: List[SourceCitation] = []
        findings: List[str] = []

        logger.info(f"Starting research task {task.id}: {task.query[:50]}...")

        # Query each enabled source
        for source_type in task.sources:
            try:
                if source_type == SourceType.HIRAG:
                    source_results = await self._query_hirag(task)
                    citations.extend(source_results)
                elif source_type == SourceType.WEB_SEARCH:
                    source_results = await self._query_web(task)
                    citations.extend(source_results)
                elif source_type == SourceType.SUPASERCH:
                    source_results = await self._query_supaserch(task)
                    citations.extend(source_results)
            except Exception as e:
                logger.warning(f"Error querying {source_type.value}: {e}")

        # Limit to max sources
        citations = sorted(citations, key=lambda c: c.relevance_score, reverse=True)
        citations = citations[:task.max_sources]

        # Synthesize findings
        if citations:
            findings = await self._synthesize_findings(task, citations)

        # Determine confidence
        confidence = self._calculate_confidence(citations)

        duration_ms = int((time.time() - start_time) * 1000)

        result = ResearchResult(
            task_id=task.id,
            summary=findings[0] if findings else "No findings available.",
            findings=findings,
            citations=citations if task.include_citations else [],
            confidence=confidence,
            duration_ms=duration_ms,
        )

        logger.info(f"Research task {task.id} completed in {duration_ms}ms with {len(citations)} sources")
        return result

    async def _query_hirag(self, task: ResearchTask) -> List[SourceCitation]:
        """Query Hi-RAG v2 knowledge base."""
        if not self.http_client:
            return []

        try:
            response = await self.http_client.post(
                f"{self.hirag_url}/hirag/query",
                json={
                    "query": task.query,
                    "top_k": task.max_sources,
                    "rerank": True,
                },
            )
            response.raise_for_status()
            data = response.json()

            citations = []
            for result in data.get("results", []):
                citations.append(SourceCitation(
                    type=SourceType.HIRAG,
                    title=result.get("title", "Knowledge Base Entry"),
                    url=result.get("source_url"),
                    excerpt=result.get("content", "")[:500],
                    relevance_score=result.get("score", 0.0),
                    metadata={"chunk_id": result.get("id")},
                ))
            return citations

        except Exception as e:
            logger.error(f"Hi-RAG query failed: {e}")
            return []

    async def _query_web(self, task: ResearchTask) -> List[SourceCitation]:
        """Query web search."""
        # Note: In production, this would use a web search API
        # For now, return empty - web search is handled by the agent's WebSearch tool
        logger.debug("Web search delegated to agent WebSearch tool")
        return []

    async def _query_supaserch(self, task: ResearchTask) -> List[SourceCitation]:
        """Query SupaSerch multimodal research."""
        # Placeholder for SupaSerch integration
        logger.debug("SupaSerch integration pending")
        return []

    async def _synthesize_findings(
        self,
        task: ResearchTask,
        citations: List[SourceCitation],
    ) -> List[str]:
        """Synthesize findings from citations."""
        # Extract key excerpts as findings
        findings = []
        for citation in citations[:5]:  # Top 5 sources
            if citation.excerpt:
                findings.append(citation.excerpt)

        if not findings:
            findings = ["Research completed but no significant findings extracted."]

        return findings

    def _calculate_confidence(self, citations: List[SourceCitation]) -> ConfidenceLevel:
        """Calculate confidence level based on sources."""
        if not citations:
            return ConfidenceLevel.UNCERTAIN

        # High confidence if multiple corroborating sources with high scores
        high_quality = [c for c in citations if c.relevance_score > 0.8]
        if len(high_quality) >= 3:
            return ConfidenceLevel.HIGH
        elif len(high_quality) >= 1 or len(citations) >= 3:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
