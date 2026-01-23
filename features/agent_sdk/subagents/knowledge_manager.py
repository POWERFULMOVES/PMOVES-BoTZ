"""
Knowledge Manager Subagent

Specialized agent for Hi-RAG knowledge base operations:
- Qdrant vector embeddings management
- Neo4j knowledge graph operations
- Meilisearch full-text indexing
- Extract Worker ingestion coordination
- Index health monitoring

Usage:
    async with KnowledgeManagerAgent("knowledge-001") as agent:
        # Query knowledge
        results = await agent.query("What is PMOVES architecture?")

        # Ingest document
        await agent.ingest_document(doc_id, content, metadata)

        # Check index health
        health = await agent.check_health()
"""

import os
from datetime import datetime
from typing import Any, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class KnowledgeManagerAgent:
    """
    Hi-RAG knowledge base management agent.

    Manages the hybrid retrieval system:
    - Qdrant: Vector embeddings for semantic search
    - Neo4j: Knowledge graph for entity relationships
    - Meilisearch: Full-text search with typo tolerance
    - Extract Worker: Ingestion and indexing pipeline

    Attributes:
        agent_id: Unique identifier
        hirag_url: Hi-RAG v2 gateway endpoint
        qdrant_url: Qdrant vector DB endpoint
        neo4j_url: Neo4j graph DB endpoint
        meilisearch_url: Meilisearch endpoint
        extract_worker_url: Extract Worker endpoint
    """

    HIRAG_URL = os.getenv("HIRAG_URL", "http://localhost:8086")
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    NEO4J_URL = os.getenv("NEO4J_URL", "http://localhost:7474")
    MEILISEARCH_URL = os.getenv("MEILISEARCH_URL", "http://localhost:7700")
    EXTRACT_WORKER_URL = os.getenv("EXTRACT_WORKER_URL", "http://localhost:8083")

    # Default collection/index names
    QDRANT_COLLECTION = "pmoves_chunks"
    MEILISEARCH_INDEX = "pmoves_chunks"

    def __init__(self, agent_id: str):
        """
        Initialize knowledge manager agent.

        Args:
            agent_id: Unique identifier for this agent
        """
        self.agent_id = agent_id
        self._http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Connect to knowledge services."""
        if HAS_HTTPX:
            self._http_client = httpx.AsyncClient(timeout=60.0)

    async def disconnect(self) -> None:
        """Disconnect from services."""
        if self._http_client:
            await self._http_client.aclose()

    async def query(
        self,
        query: str,
        top_k: int = 10,
        rerank: bool = True,
        sources: Optional[list[str]] = None,
    ) -> dict:
        """
        Query the knowledge base using Hi-RAG v2.

        Args:
            query: Search query
            top_k: Number of results
            rerank: Apply cross-encoder reranking
            sources: Limit to specific sources (vector, graph, fulltext)

        Returns:
            Query results with scores and sources
        """
        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        try:
            payload = {
                "query": query,
                "top_k": top_k,
                "rerank": rerank,
            }
            if sources:
                payload["sources"] = sources

            response = await self._http_client.post(
                f"{self.HIRAG_URL}/hirag/query",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def ingest_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[dict] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> dict:
        """
        Ingest a document into the knowledge base.

        Args:
            doc_id: Document identifier
            content: Document text content
            metadata: Additional metadata
            chunk_size: Chunk size for splitting
            chunk_overlap: Overlap between chunks

        Returns:
            Ingestion result
        """
        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        try:
            response = await self._http_client.post(
                f"{self.EXTRACT_WORKER_URL}/ingest",
                json={
                    "id": doc_id,
                    "text": content,
                    "metadata": metadata or {},
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def delete_document(self, doc_id: str) -> dict:
        """
        Delete a document from all indexes.

        Args:
            doc_id: Document identifier

        Returns:
            Deletion result
        """
        results = {"doc_id": doc_id, "deleted_from": []}

        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        # Delete from Qdrant
        try:
            response = await self._http_client.post(
                f"{self.QDRANT_URL}/collections/{self.QDRANT_COLLECTION}/points/delete",
                json={
                    "filter": {
                        "must": [
                            {"key": "doc_id", "match": {"value": doc_id}}
                        ]
                    }
                },
            )
            if response.status_code == 200:
                results["deleted_from"].append("qdrant")
        except Exception:
            pass

        # Delete from Meilisearch
        try:
            response = await self._http_client.post(
                f"{self.MEILISEARCH_URL}/indexes/{self.MEILISEARCH_INDEX}/documents/delete",
                json={"filter": f"doc_id = {doc_id}"},
            )
            if response.status_code in [200, 202]:
                results["deleted_from"].append("meilisearch")
        except Exception:
            pass

        return results

    async def check_health(self) -> dict:
        """
        Check health of all knowledge services.

        Returns:
            Health status for each service
        """
        health = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": {},
        }

        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        # Check Hi-RAG
        try:
            response = await self._http_client.get(
                f"{self.HIRAG_URL}/healthz",
                timeout=5.0,
            )
            health["services"]["hirag"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000,
            }
        except Exception as e:
            health["services"]["hirag"] = {"status": "offline", "error": str(e)}

        # Check Qdrant
        try:
            response = await self._http_client.get(
                f"{self.QDRANT_URL}/healthz",
                timeout=5.0,
            )
            health["services"]["qdrant"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
            }
        except Exception as e:
            health["services"]["qdrant"] = {"status": "offline", "error": str(e)}

        # Check Meilisearch
        try:
            response = await self._http_client.get(
                f"{self.MEILISEARCH_URL}/health",
                timeout=5.0,
            )
            health["services"]["meilisearch"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
            }
        except Exception as e:
            health["services"]["meilisearch"] = {"status": "offline", "error": str(e)}

        # Check Neo4j
        try:
            response = await self._http_client.get(
                f"{self.NEO4J_URL}/",
                timeout=5.0,
            )
            health["services"]["neo4j"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
            }
        except Exception as e:
            health["services"]["neo4j"] = {"status": "offline", "error": str(e)}

        # Overall status
        statuses = [s.get("status") for s in health["services"].values()]
        health["overall"] = "healthy" if all(s == "healthy" for s in statuses) else "degraded"

        return health

    async def get_stats(self) -> dict:
        """
        Get statistics from all indexes.

        Returns:
            Index statistics
        """
        stats = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "indexes": {},
        }

        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        # Qdrant collection info
        try:
            response = await self._http_client.get(
                f"{self.QDRANT_URL}/collections/{self.QDRANT_COLLECTION}",
            )
            if response.status_code == 200:
                data = response.json()
                stats["indexes"]["qdrant"] = {
                    "vectors_count": data.get("result", {}).get("vectors_count", 0),
                    "points_count": data.get("result", {}).get("points_count", 0),
                }
        except Exception:
            stats["indexes"]["qdrant"] = {"error": "unavailable"}

        # Meilisearch stats
        try:
            response = await self._http_client.get(
                f"{self.MEILISEARCH_URL}/indexes/{self.MEILISEARCH_INDEX}/stats",
            )
            if response.status_code == 200:
                data = response.json()
                stats["indexes"]["meilisearch"] = {
                    "documents_count": data.get("numberOfDocuments", 0),
                    "is_indexing": data.get("isIndexing", False),
                }
        except Exception:
            stats["indexes"]["meilisearch"] = {"error": "unavailable"}

        return stats

    async def similarity_search(
        self,
        text: str,
        top_k: int = 5,
    ) -> dict:
        """
        Perform similarity search using embeddings only.

        Args:
            text: Text to find similar documents for
            top_k: Number of results

        Returns:
            Similar documents with scores
        """
        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        try:
            response = await self._http_client.post(
                f"{self.HIRAG_URL}/hirag/query",
                json={
                    "query": text,
                    "top_k": top_k,
                    "sources": ["vector"],  # Vector-only search
                    "rerank": False,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def graph_query(
        self,
        entity: str,
        relationship: Optional[str] = None,
        depth: int = 2,
    ) -> dict:
        """
        Query the knowledge graph.

        Args:
            entity: Starting entity name
            relationship: Optional relationship type filter
            depth: Traversal depth

        Returns:
            Graph query results
        """
        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        try:
            # Construct Cypher query
            if relationship:
                cypher = f"""
                    MATCH (e)-[r:{relationship}*1..{depth}]-(related)
                    WHERE e.name =~ '(?i).*{entity}.*'
                    RETURN e, r, related
                    LIMIT 50
                """
            else:
                cypher = f"""
                    MATCH (e)-[r*1..{depth}]-(related)
                    WHERE e.name =~ '(?i).*{entity}.*'
                    RETURN e, r, related
                    LIMIT 50
                """

            response = await self._http_client.post(
                f"{self.NEO4J_URL}/db/neo4j/tx/commit",
                json={
                    "statements": [{"statement": cypher}]
                },
                auth=("neo4j", os.getenv("NEO4J_PASSWORD", "password")),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False
