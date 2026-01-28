"""
Media Slice - Data Models.

Defines data structures for media processing tasks.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class MediaType(Enum):
    """Types of media."""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"


class ProcessingStage(Enum):
    """Stages of media processing."""
    INGESTION = "ingestion"
    TRANSCRIPTION = "transcription"
    ANALYSIS = "analysis"
    EMBEDDING = "embedding"
    STORAGE = "storage"
    COMPLETE = "complete"


@dataclass
class MediaArtifact:
    """An artifact produced during media processing."""
    type: str  # transcript, summary, embedding, thumbnail
    content: Any
    format: str = "text"  # text, json, binary, url
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "content": self.content if self.format != "binary" else f"<binary:{self.size_bytes}bytes>",
            "format": self.format,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
        }


@dataclass
class MediaTask:
    """A media processing task specification."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_url: str = ""
    media_type: MediaType = MediaType.VIDEO
    operations: List[str] = field(default_factory=lambda: ["transcribe", "summarize"])
    output_formats: List[str] = field(default_factory=lambda: ["text", "json"])
    language: str = "en"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source_url": self.source_url,
            "media_type": self.media_type.value,
            "operations": self.operations,
            "output_formats": self.output_formats,
            "language": self.language,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class MediaResult:
    """Result of a media processing task."""
    task_id: str
    stage: ProcessingStage = ProcessingStage.COMPLETE
    artifacts: List[MediaArtifact] = field(default_factory=list)
    transcript: Optional[str] = None
    summary: Optional[str] = None
    duration_seconds: float = 0.0
    completed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    processing_time_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "stage": self.stage.value,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "transcript": self.transcript,
            "summary": self.summary,
            "duration_seconds": self.duration_seconds,
            "completed_at": self.completed_at,
            "processing_time_ms": self.processing_time_ms,
            "error": self.error,
        }
