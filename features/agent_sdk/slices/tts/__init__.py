"""
TTS Slice - Text-to-Speech Synthesis.

This vertical slice provides TTS capabilities for the Agent SDK:
- api.py: TTS endpoints for SDK agents
- service.py: TTS engine routing and synthesis
- models.py: Voice personas and configurations
- SKILL.md: Agent context for TTS tasks

Reference: docs/agents/PMOVES_Engine_Templates.md

Use: from slices.tts import TTSService, VoicePersona
"""

from .models import (
    DEFAULT_PUNCTUATION_RULES,
    DEFAULT_VOICES,
    EmotionStyle,
    MultiSpeakerRequest,
    MultiSpeakerSegment,
    PunctuationRule,
    TTSEngine,
    TTSRequest,
    TTSResult,
    VoiceConfig,
    VoicePersona,
)
from .service import TTSService
from .. import register_slice

# Register this slice
register_slice("tts")(TTSService)

__all__ = [
    "DEFAULT_PUNCTUATION_RULES",
    "DEFAULT_VOICES",
    "EmotionStyle",
    "MultiSpeakerRequest",
    "MultiSpeakerSegment",
    "PunctuationRule",
    "TTSEngine",
    "TTSRequest",
    "TTSResult",
    "TTSService",
    "VoiceConfig",
    "VoicePersona",
]
