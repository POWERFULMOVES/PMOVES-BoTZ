"""
Media Processor Subagent

Specialized agent for video/audio processing workflows:
- YouTube ingestion via PMOVES.YT
- Transcription via FFmpeg-Whisper
- Object detection via YOLOv8 (Media-Video Analyzer)
- Audio analysis (emotion/speaker detection)
- MinIO artifact storage

Usage:
    async with MediaProcessorAgent("media-001") as agent:
        result = await agent.process_video(
            url="https://youtube.com/watch?v=xxx",
            analyze_objects=True,
            analyze_audio=True
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


class MediaProcessorAgent:
    """
    Video/audio processing agent for PMOVES media pipeline.

    Coordinates with:
    - PMOVES.YT: YouTube video ingestion
    - FFmpeg-Whisper: Speech-to-text transcription
    - Media-Video Analyzer: YOLOv8 object detection
    - Media-Audio Analyzer: Emotion/speaker analysis
    - MinIO: Artifact storage
    - Extract Worker: Text embedding

    Attributes:
        agent_id: Unique identifier
        pmoves_yt_url: PMOVES.YT service endpoint
        whisper_url: FFmpeg-Whisper endpoint
        video_analyzer_url: Video analyzer endpoint
        audio_analyzer_url: Audio analyzer endpoint
    """

    PMOVES_YT_URL = os.getenv("PMOVES_YT_URL", "http://localhost:8077")
    WHISPER_URL = os.getenv("WHISPER_URL", "http://localhost:8078")
    VIDEO_ANALYZER_URL = os.getenv("VIDEO_ANALYZER_URL", "http://localhost:8079")
    AUDIO_ANALYZER_URL = os.getenv("AUDIO_ANALYZER_URL", "http://localhost:8082")
    EXTRACT_WORKER_URL = os.getenv("EXTRACT_WORKER_URL", "http://localhost:8083")
    NATS_URL = os.getenv("NATS_URL", "nats://nats:pmoves@nats:4222")

    def __init__(self, agent_id: str):
        """
        Initialize media processor agent.

        Args:
            agent_id: Unique identifier for this agent
        """
        self.agent_id = agent_id
        self._http_client: Optional[httpx.AsyncClient] = None
        self._nats_client = None

    async def connect(self) -> None:
        """Connect to media services."""
        if HAS_HTTPX:
            self._http_client = httpx.AsyncClient(timeout=300.0)  # Long timeout for media

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

    async def ingest_youtube(
        self,
        url: str,
        auto_transcribe: bool = True,
        auto_analyze: bool = False,
    ) -> dict:
        """
        Ingest a YouTube video.

        Args:
            url: YouTube video URL
            auto_transcribe: Whether to auto-transcribe
            auto_analyze: Whether to run full analysis

        Returns:
            Ingestion result with video ID and status
        """
        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        try:
            response = await self._http_client.post(
                f"{self.PMOVES_YT_URL}/yt/ingest",
                json={
                    "url": url,
                    "auto_transcribe": auto_transcribe,
                    "auto_analyze": auto_analyze,
                },
            )
            response.raise_for_status()
            result = response.json()

            # Publish event
            await self._publish_event("ingest.video.started.v1", {
                "video_id": result.get("video_id"),
                "url": url,
                "agent_id": self.agent_id,
            })

            return result
        except Exception as e:
            return {"error": str(e)}

    async def transcribe(
        self,
        file_path: str,
        language: str = "auto",
        model: str = "small",
    ) -> dict:
        """
        Transcribe audio/video file.

        Args:
            file_path: Path to media file (in MinIO)
            language: Language code or "auto"
            model: Whisper model size

        Returns:
            Transcription result
        """
        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        try:
            response = await self._http_client.post(
                f"{self.WHISPER_URL}/transcribe",
                json={
                    "file_path": file_path,
                    "language": language,
                    "model": model,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def analyze_video(
        self,
        file_path: str,
        frame_interval: int = 5,
        confidence_threshold: float = 0.25,
    ) -> dict:
        """
        Analyze video for objects/scenes using YOLOv8.

        Args:
            file_path: Path to video file
            frame_interval: Analyze every Nth frame
            confidence_threshold: Detection confidence threshold

        Returns:
            Analysis results with detected objects
        """
        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        try:
            response = await self._http_client.post(
                f"{self.VIDEO_ANALYZER_URL}/analyze",
                json={
                    "file_path": file_path,
                    "frame_interval": frame_interval,
                    "confidence_threshold": confidence_threshold,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def analyze_audio(
        self,
        file_path: str,
        detect_emotions: bool = True,
        detect_speakers: bool = True,
    ) -> dict:
        """
        Analyze audio for emotions and speaker detection.

        Args:
            file_path: Path to audio file
            detect_emotions: Whether to detect emotions
            detect_speakers: Whether to detect speakers

        Returns:
            Analysis results
        """
        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        try:
            response = await self._http_client.post(
                f"{self.AUDIO_ANALYZER_URL}/analyze",
                json={
                    "file_path": file_path,
                    "detect_emotions": detect_emotions,
                    "detect_speakers": detect_speakers,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def process_video(
        self,
        url: str,
        transcribe: bool = True,
        analyze_objects: bool = False,
        analyze_audio: bool = False,
    ) -> dict:
        """
        Full video processing pipeline.

        Args:
            url: YouTube URL or file path
            transcribe: Run transcription
            analyze_objects: Run object detection
            analyze_audio: Run audio analysis

        Returns:
            Combined processing results
        """
        results = {
            "url": url,
            "agent_id": self.agent_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stages": {},
        }

        # Ingest
        if url.startswith("http"):
            ingest_result = await self.ingest_youtube(url, auto_transcribe=transcribe)
            results["stages"]["ingest"] = ingest_result
            if "error" in ingest_result:
                return results

        # Additional analysis stages would be triggered via NATS
        # and processed asynchronously

        await self._publish_event("media.pipeline.started.v1", {
            "url": url,
            "agent_id": self.agent_id,
            "stages": ["ingest", "transcribe"] +
                     (["objects"] if analyze_objects else []) +
                     (["audio"] if analyze_audio else []),
        })

        return results

    async def index_transcript(
        self,
        transcript_id: str,
        text: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Index transcript text for search.

        Args:
            transcript_id: Unique ID for transcript
            text: Transcript text content
            metadata: Additional metadata

        Returns:
            Indexing result
        """
        if not self._http_client:
            return {"error": "HTTP client not initialized"}

        try:
            response = await self._http_client.post(
                f"{self.EXTRACT_WORKER_URL}/ingest",
                json={
                    "id": transcript_id,
                    "text": text,
                    "metadata": metadata or {},
                    "source_type": "transcript",
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def _publish_event(self, subject: str, payload: dict) -> None:
        """Publish event to NATS."""
        if self._nats_client:
            import json
            payload["timestamp"] = datetime.utcnow().isoformat() + "Z"
            await self._nats_client.publish(
                subject,
                json.dumps(payload).encode(),
            )

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False
