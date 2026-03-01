"""
Researcher Subagent

Specialized agent for deep research tasks using:
- Hi-RAG v2 for semantic knowledge retrieval
- SupaSerch for multimodal holographic research
- DeepResearch for LLM-based research planning
- Web search for current information

Usage:
    async with ResearcherAgent("research-001") as agent:
        result = await agent.research(
            query="Latest developments in quantum computing",
            depth="comprehensive",
            sources=["knowledge_base", "web", "papers"]
        )
"""

import os
from datetime import datetime
from typing import Any, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import nats
    HAS_NATS = True
except ImportError:
    HAS_NATS = False


class ResearcherAgent:
    """
    Deep research agent with multi-source capabilities.

    Integrates with PMOVES research infrastructure:
    - Hi-RAG v2: Hybrid vector + graph + full-text search
    - SupaSerch: Orchestrated multimodal research
    - DeepResearch: LLM research planning
    - Web Search: Current information retrieval

    Attributes:
        agent_id: Unique identifier
        hirag_url: Hi-RAG v2 endpoint
        supaserch_url: SupaSerch endpoint
        nats_url: NATS message bus URL
    """

    HIRAG_URL = os.getenv("HIRAG_URL", "http://localhost:8086")
    SUPASERCH_URL = os.getenv("SUPASERCH_URL", "http://localhost:8099")
    DEEPRESEARCH_URL = os.getenv("DEEPRESEARCH_URL", "http://localhost:8098")
    NATS_URL = os.getenv("NATS_URL", "nats://nats:pmoves@nats:4222")

    def __init__(self, agent_id: str):
        """
        Initialize researcher agent.

        Args:
            agent_id: Unique identifier for this agent
        """
        self.agent_id = agent_id
        self._http_client: Optional[httpx.AsyncClient] = None
        self._nats_client = None

    async def connect(self) -> None:
        """Connect to research services."""
        if HAS_HTTPX:
            self._http_client = httpx.AsyncClient(timeout=120.0)

        if HAS_NATS:
            try:
                self._nats_client = await nats.connect(self.NATS_URL)
            except Exception:
                self._nats_client = None

    async def disconnect(self) -> None:
        """Disconnect from services."""
        if self._http_client:
            await self._http_client.aclose()
        if self._nats_client:
            await self._nats_client.close()

    async def research(
        self,
        query: str,
        depth: str = "detailed",
        sources: Optional[list[str]] = None,
        max_results: int = 20,
    ) -> dict:
        """
        Execute a research query across multiple sources.

        Args:
            query: Research question or topic
            depth: Research depth (basic, detailed, comprehensive)
            sources: List of sources (knowledge_base, web, papers, all)
            max_results: Maximum results per source

        Returns:
            Research results with findings, sources, and confidence
        """
        sources = sources or ["knowledge_base", "web"]
        results = {
            "query": query,
            "depth": depth,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "findings": [],
            "sources_queried": [],
            "methodology": [],
        }

        # Query Hi-RAG for knowledge base
        if "knowledge_base" in sources or "all" in sources:
            hirag_results = await self._query_hirag(query, max_results)
            if hirag_results:
                results["findings"].extend(hirag_results.get("results", []))
                results["sources_queried"].append("hi-rag-v2")
                results["methodology"].append("Hybrid vector + graph + full-text search")

        # Query SupaSerch for comprehensive research
        if "all" in sources or depth == "comprehensive":
            supaserch_results = await self._query_supaserch(query)
            if supaserch_results:
                results["findings"].extend(supaserch_results.get("results", []))
                results["sources_queried"].append("supaserch")
                results["methodology"].append("Multimodal holographic research")

        # Trigger DeepResearch for planning
        if depth == "comprehensive":
            await self._trigger_deepresearch(query)
            results["methodology"].append("LLM-based research planning (async)")

        # Calculate confidence based on source coverage
        results["confidence"] = self._calculate_confidence(results)

        return results

    async def _query_hirag(self, query: str, top_k: int = 10) -> Optional[dict]:
        """Query Hi-RAG v2 knowledge base."""
        if not self._http_client:
            return None

        try:
            response = await self._http_client.post(
                f"{self.HIRAG_URL}/hirag/query",
                json={
                    "query": query,
                    "top_k": top_k,
                    "rerank": True,
                },
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    async def _query_supaserch(self, query: str) -> Optional[dict]:
        """Query SupaSerch for comprehensive research."""
        if not self._http_client:
            return None

        try:
            response = await self._http_client.post(
                f"{self.SUPASERCH_URL}/search",
                json={
                    "query": query,
                    "use_deep_research": True,
                    "use_hirag": True,
                },
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    async def _trigger_deepresearch(self, query: str) -> None:
        """Trigger DeepResearch via NATS."""
        if not self._nats_client:
            return

        try:
            import json
            import uuid
            await self._nats_client.publish(
                "research.deepresearch.request.v1",
                json.dumps({
                    "query": query,
                    "request_id": str(uuid.uuid4()),
                    "requester": self.agent_id,
                    "options": {
                        "depth": "comprehensive",
                        "sources": ["web", "knowledge_base", "papers"],
                    },
                }).encode(),
            )
        except Exception:
            pass

    def _calculate_confidence(self, results: dict) -> float:
        """Calculate confidence score based on results."""
        base_confidence = 0.5

        # More sources = higher confidence
        source_count = len(results.get("sources_queried", []))
        base_confidence += min(source_count * 0.1, 0.3)

        # More findings = higher confidence
        finding_count = len(results.get("findings", []))
        base_confidence += min(finding_count * 0.02, 0.2)

        return min(base_confidence, 0.95)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False
