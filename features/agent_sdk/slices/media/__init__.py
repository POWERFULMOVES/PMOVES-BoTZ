"""
Media Slice - Video/Audio Processing.

This vertical slice encapsulates all media processing functionality:
- api.py: Media task endpoints
- service.py: Processing orchestration
- models.py: Media data structures
- SKILL.md: Agent context for media tasks

Use: from slices.media import MediaService
"""

from .service import MediaService
from .models import MediaTask, MediaResult, MediaType, ProcessingStage
from .. import register_slice

# Register this slice
register_slice("media")(MediaService)

__all__ = [
    "MediaService",
    "MediaTask",
    "MediaResult",
    "MediaType",
    "ProcessingStage",
]
