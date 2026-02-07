"""
Media Slice - Service Layer.

Orchestrates media processing workflows:
- PMOVES.YT for YouTube ingestion
- FFmpeg-Whisper for transcription
- TensorZero for embeddings and analysis
- MinIO for artifact storage
"""

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .models import (
    MediaArtifact,
    MediaResult,
    MediaTask,
    MediaType,
    ProcessingStage,
)

logger = logging.getLogger(__name__)


class MediaService:
    """
    Media Service - Orchestrates video/audio processing workflows.

    This service encapsulates all media processing logic in a single vertical slice.

    Usage:
        service = MediaService(http_client=client)
        task = MediaTask(
            source_url="https://youtube.com/watch?v=...",
            operations=["transcribe", "summarize"],
        )
        result = await service.execute(task)
        print(result.transcript)
    """

    def __init__(
        self,
        http_client: Optional[Any] = None,
        yt_service_url: str = "http://localhost:8089",
        whisper_url: str = "http://localhost:9000",
        minio_url: str = "http://localhost:9001",
    ):
        """
        Initialize Media Service.

        Args:
            http_client: Async HTTP client
            yt_service_url: PMOVES.YT service URL
            whisper_url: FFmpeg-Whisper service URL
            minio_url: MinIO storage URL
        """
        self.http_client = http_client
        self.yt_service_url = yt_service_url
        self.whisper_url = whisper_url
        self.minio_url = minio_url

    async def execute(self, task: MediaTask) -> MediaResult:
        """
        Execute a media processing task.

        Args:
            task: Media task specification

        Returns:
            MediaResult with artifacts and transcript
        """
        start_time = time.time()
        artifacts: List[MediaArtifact] = []
        transcript: Optional[str] = None
        summary: Optional[str] = None
        error: Optional[str] = None

        logger.info(f"Starting media task {task.id} for {task.source_url[:50]}...")

        try:
            # Stage 1: Ingestion
            if task.media_type == MediaType.VIDEO:
                media_data = await self._ingest_video(task)
            elif task.media_type == MediaType.AUDIO:
                media_data = await self._ingest_audio(task)
            else:
                media_data = {"url": task.source_url}

            # Stage 2: Transcription
            if "transcribe" in task.operations:
                transcript = await self._transcribe(media_data, task.language)
                artifacts.append(MediaArtifact(
                    type="transcript",
                    content=transcript,
                    format="text",
                    size_bytes=len(transcript.encode()) if transcript else 0,
                ))

            # Stage 3: Summarization
            if "summarize" in task.operations and transcript:
                summary = await self._summarize(transcript)
                artifacts.append(MediaArtifact(
                    type="summary",
                    content=summary,
                    format="text",
                    size_bytes=len(summary.encode()) if summary else 0,
                ))

            # Stage 4: Embeddings
            if "embed" in task.operations and transcript:
                embeddings = await self._generate_embeddings(transcript)
                artifacts.append(MediaArtifact(
                    type="embeddings",
                    content=embeddings,
                    format="json",
                    metadata={"dimensions": len(embeddings) if embeddings else 0},
                ))

        except Exception as e:
            logger.error(f"Media task {task.id} failed: {e}")
            error = str(e)

        processing_time_ms = int((time.time() - start_time) * 1000)

        result = MediaResult(
            task_id=task.id,
            stage=ProcessingStage.COMPLETE if not error else ProcessingStage.ANALYSIS,
            artifacts=artifacts,
            transcript=transcript,
            summary=summary,
            processing_time_ms=processing_time_ms,
            error=error,
        )

        logger.info(f"Media task {task.id} completed in {processing_time_ms}ms")
        return result

    async def _ingest_video(self, task: MediaTask) -> Dict:
        """Ingest video from source URL."""
        if not self.http_client:
            return {"url": task.source_url, "local_path": None}

        # Check if YouTube URL using proper URL parsing
        if self._is_youtube_url(task.source_url):
            try:
                response = await self.http_client.post(
                    f"{self.yt_service_url}/ingest",
                    json={"url": task.source_url},
                    timeout=60.0,  # 60 second timeout for ingestion
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"YouTube ingestion failed: {e}")

        return {"url": task.source_url}

    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL using proper URL parsing."""
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            # Remove www. prefix if present
            if host.startswith("www."):
                host = host[4:]
            # Check for exact YouTube domains
            return host in ("youtube.com", "youtu.be", "m.youtube.com")
        except Exception:
            return False

    async def _ingest_audio(self, task: MediaTask) -> Dict:
        """Ingest audio from source URL."""
        return {"url": task.source_url}

    async def _transcribe(self, media_data: Dict, language: str) -> Optional[str]:
        """Transcribe media using Whisper."""
        if not self.http_client:
            return None

        try:
            response = await self.http_client.post(
                f"{self.whisper_url}/transcribe",
                json={
                    "url": media_data.get("url") or media_data.get("local_path"),
                    "language": language,
                },
                timeout=300.0,  # Transcription can be slow
            )
            response.raise_for_status()
            data = response.json()
            return data.get("text", "")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    async def _summarize(self, transcript: str) -> Optional[str]:
        """Summarize transcript using LLM."""
        # Placeholder - in production, this would call TensorZero
        if len(transcript) < 100:
            return transcript
        return f"Summary of {len(transcript)} character transcript (summarization pending)"

    async def _generate_embeddings(self, text: str) -> Optional[List[float]]:
        """Generate embeddings for text."""
        # Placeholder - in production, this would call TensorZero embeddings
        return None
