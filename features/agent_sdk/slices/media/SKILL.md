# Media Processing Skill

**Slice:** `slices/media/`
**Type:** Audio/Video Processing

## Purpose

Video and audio processing workflows. Use this skill when:
- YouTube videos need transcription
- Audio files need speech-to-text
- Media needs embedding for search
- Content summarization is required

## Quick Start

```python
from slices.media import MediaService, MediaTask, MediaType

service = MediaService(http_client=client)
task = MediaTask(
    source_url="https://youtube.com/watch?v=example",
    media_type=MediaType.VIDEO,
    operations=["transcribe", "summarize"],
)
result = await service.execute(task)
print(result.transcript)
```

## API Reference

### MediaService

| Method | Description | Returns |
|--------|-------------|---------|
| `execute(task)` | Execute media processing | `MediaResult` |

### Operations

| Operation | Description | Output |
|-----------|-------------|--------|
| `transcribe` | Speech-to-text via Whisper | transcript text |
| `summarize` | LLM-based summarization | summary text |
| `embed` | Generate vector embeddings | float array |

### Media Types

- **VIDEO**: YouTube, MP4, WebM
- **AUDIO**: MP3, WAV, M4A
- **IMAGE**: Screenshots, thumbnails
- **DOCUMENT**: PDFs with embedded media

## Processing Pipeline

```
Source URL
    ↓
[Ingestion] → Download/extract media
    ↓
[Transcription] → Whisper STT
    ↓
[Analysis] → LLM summarization
    ↓
[Embedding] → TensorZero vectors
    ↓
[Storage] → MinIO artifacts
```

## Integration Points

| Service | URL | Purpose |
|---------|-----|---------|
| PMOVES.YT | localhost:8089 | YouTube ingestion |
| FFmpeg-Whisper | localhost:9000 | Transcription |
| TensorZero | localhost:3030 | Embeddings |
| MinIO | localhost:9001 | Artifact storage |

## Example: YouTube Processing

```python
# Full YouTube video processing
task = MediaTask(
    source_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
    media_type=MediaType.VIDEO,
    operations=["transcribe", "summarize", "embed"],
    language="en",
)
result = await service.execute(task)

# Access results
print(f"Transcript: {result.transcript[:200]}...")
print(f"Summary: {result.summary}")
print(f"Artifacts: {[a.type for a in result.artifacts]}")
```
