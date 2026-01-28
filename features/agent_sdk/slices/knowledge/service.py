"""
Knowledge Slice - Service Layer.

Hi-RAG v2 knowledge management:
- Qdrant for vector embeddings
- Neo4j for knowledge graph
- Meilisearch for full-text search
- Cross-encoder reranking for relevance
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .models import (
    IndexOperation,
    KnowledgeChunk,
    KnowledgeResult,
    KnowledgeTask,
    RetrievalMode,
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """
    Knowledge Service - Hi-RAG v2 knowledge management.

    This service encapsulates all knowledge base operations in a single vertical slice.

    Usage:
        service = KnowledgeService(http_client=client)

        # Query knowledge
        task = KnowledgeTask(query="How does TensorZero work?")
        result = await service.execute(task)
        for chunk in result.chunks:
            print(f"{chunk.score:.2f}: {chunk.content[:100]}")

        # Ingest documents
        task = KnowledgeTask(
            operation=IndexOperation.INGEST,
            documents=[{"content": "...", "source": "doc.pdf"}],
        )
        result = await service.execute(task)
    """

    def __init__(
        self,
        http_client: Optional[Any] = None,
        hirag_url: str = "http://localhost:8086",
        qdrant_url: str = "http://localhost:6333",
        meilisearch_url: str = "http://localhost:7700",
    ):
        """
        Initialize Knowledge Service.

        Args:
            http_client: Async HTTP client
            hirag_url: Hi-RAG v2 service URL
            qdrant_url: Qdrant vector DB URL
            meilisearch_url: Meilisearch URL
        """
        self.http_client = http_client
        self.hirag_url = hirag_url
        self.qdrant_url = qdrant_url
        self.meilisearch_url = meilisearch_url

    async def execute(self, task: KnowledgeTask) -> KnowledgeResult:
        """
        Execute a knowledge management task.

        Args:
            task: Knowledge task specification

        Returns:
            KnowledgeResult with chunks or processing status
        """
        start_time = time.time()

        if task.operation == IndexOperation.RETRIEVE:
            result = await self._retrieve(task)
        elif task.operation == IndexOperation.INGEST:
            result = await self._ingest(task)
        elif task.operation == IndexOperation.UPDATE:
            result = await self._update(task)
        elif task.operation == IndexOperation.DELETE:
            result = await self._delete(task)
        elif task.operation == IndexOperation.REINDEX:
            result = await self._reindex(task)
        else:
            # Unknown operation - error
            result = KnowledgeResult(
                task_id=task.id,
                error=f"Unknown operation: {task.operation}",
            )

        result.duration_ms = int((time.time() - start_time) * 1000)
        return result

    async def _retrieve(self, task: KnowledgeTask) -> KnowledgeResult:
        """Retrieve knowledge chunks matching query."""
        if not task.query:
            return KnowledgeResult(
                task_id=task.id,
                error="Query is required for retrieval",
            )

        if not self.http_client:
            return KnowledgeResult(
                task_id=task.id,
                error="HTTP client not configured",
            )

        logger.info(f"Retrieving knowledge for: {task.query[:50]}...")

        try:
            response = await self.http_client.post(
                f"{self.hirag_url}/hirag/query",
                json={
                    "query": task.query,
                    "top_k": task.top_k,
                    "rerank": task.rerank,
                    "mode": task.retrieval_mode.value,
                    "filters": task.filters,
                },
            )
            response.raise_for_status()
            data = response.json()

            chunks = []
            for result in data.get("results", []):
                chunks.append(KnowledgeChunk(
                    id=result.get("id", ""),
                    content=result.get("content", ""),
                    source=result.get("source", "unknown"),
                    score=result.get("score", 0.0),
                    metadata=result.get("metadata", {}),
                ))

            return KnowledgeResult(
                task_id=task.id,
                chunks=chunks,
                total_found=data.get("total", len(chunks)),
                retrieval_mode_used=task.retrieval_mode,
            )

        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {e}")
            return KnowledgeResult(
                task_id=task.id,
                error=str(e),
            )

    async def _ingest(self, task: KnowledgeTask) -> KnowledgeResult:
        """Ingest documents into knowledge base."""
        if not task.documents:
            return KnowledgeResult(
                task_id=task.id,
                error="Documents are required for ingestion",
            )

        if not self.http_client:
            return KnowledgeResult(
                task_id=task.id,
                error="HTTP client not configured",
            )

        logger.info(f"Ingesting {len(task.documents)} documents...")

        try:
            response = await self.http_client.post(
                f"{self.hirag_url}/hirag/ingest",
                json={
                    "documents": task.documents,
                    "metadata": task.metadata,
                },
                timeout=300.0,  # Ingestion can be slow
            )
            response.raise_for_status()
            data = response.json()

            return KnowledgeResult(
                task_id=task.id,
                documents_processed=data.get("processed", len(task.documents)),
                total_found=data.get("total_chunks", 0),
            )

        except Exception as e:
            logger.error(f"Knowledge ingestion failed: {e}")
            return KnowledgeResult(
                task_id=task.id,
                error=str(e),
            )

    async def _update(self, task: KnowledgeTask) -> KnowledgeResult:
        """Update existing documents in knowledge base."""
        # Placeholder - update is similar to ingest with upsert semantics
        return await self._ingest(task)

    async def _delete(self, task: KnowledgeTask) -> KnowledgeResult:
        """Delete documents from knowledge base."""
        if not self.http_client:
            return KnowledgeResult(
                task_id=task.id,
                error="HTTP client not configured",
            )

        try:
            response = await self.http_client.post(
                f"{self.hirag_url}/hirag/delete",
                json={
                    "filters": task.filters,
                    "document_ids": [d.get("id") for d in task.documents if d.get("id")],
                },
            )
            response.raise_for_status()
            data = response.json()

            return KnowledgeResult(
                task_id=task.id,
                documents_processed=data.get("deleted", 0),
            )

        except Exception as e:
            logger.error(f"Knowledge deletion failed: {e}")
            return KnowledgeResult(
                task_id=task.id,
                error=str(e),
            )

    async def _reindex(self, task: KnowledgeTask) -> KnowledgeResult:
        """Trigger full reindex of knowledge base."""
        if not self.http_client:
            return KnowledgeResult(
                task_id=task.id,
                error="HTTP client not configured",
            )

        logger.info("Triggering full knowledge base reindex...")

        try:
            response = await self.http_client.post(
                f"{self.hirag_url}/hirag/reindex",
                json={
                    "filters": task.filters,
                    "metadata": task.metadata,
                },
                timeout=600.0,  # Reindex can take a long time
            )
            response.raise_for_status()
            data = response.json()

            return KnowledgeResult(
                task_id=task.id,
                documents_processed=data.get("reindexed", 0),
                total_found=data.get("total_documents", 0),
            )

        except Exception as e:
            logger.error(f"Knowledge reindex failed: {e}")
            return KnowledgeResult(
                task_id=task.id,
                error=str(e),
            )

    async def health_check(self) -> Dict[str, bool]:
        """Check health of knowledge services."""
        status = {
            "hirag": False,
            "qdrant": False,
            "meilisearch": False,
        }

        if not self.http_client:
            return status

        try:
            resp = await self.http_client.get(f"{self.hirag_url}/health")
            status["hirag"] = resp.status_code == 200
        except Exception:
            pass

        try:
            resp = await self.http_client.get(f"{self.qdrant_url}/health")
            status["qdrant"] = resp.status_code == 200
        except Exception:
            pass

        try:
            resp = await self.http_client.get(f"{self.meilisearch_url}/health")
            status["meilisearch"] = resp.status_code == 200
        except Exception:
            pass

        return status
