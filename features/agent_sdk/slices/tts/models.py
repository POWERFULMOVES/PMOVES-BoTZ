"""
TTS Slice - Data Models.

Defines data structures for text-to-speech synthesis:
- Voice personas (Host, Architect, Ops/Engineer)
- TTS engine configurations
- Punctuation engineering rules
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class TTSEngine(Enum):
    """Supported TTS engines."""
    KOKORO = "kokoro"           # Natural flow, punctuation engineering
    FISH_SPEECH = "fish_speech" # Reference audio cloning
    INDEXTTS2 = "indextts2"     # Emotion prompts
    VIBEVOICE = "vibevoice"     # Multi-speaker
    ELEVENLABS = "elevenlabs"   # Cloud TTS
    OPENAI = "openai"           # OpenAI TTS


class VoicePersona(Enum):
    """Voice personas for PMOVES.AI content."""
    HOST = "host"           # Natural, warm narration (KOKORO)
    ARCHITECT = "architect" # Fast tech jargon (FISH_SPEECH)
    OPS = "ops"             # Gritty, authoritative (INDEXTTS2)
    NEUTRAL = "neutral"     # Default voice


class EmotionStyle(Enum):
    """Emotion styles for TTS."""
    NEUTRAL = "neutral"
    AUTHORITATIVE = "authoritative"
    EXCITED = "excited"
    WHISPER = "whisper"
    SERIOUS = "serious"
    WARM = "warm"


@dataclass
class PunctuationRule:
    """Punctuation engineering rule for TTS."""
    pattern: str           # Pattern to match (e.g., "...")
    replacement: str       # SSML or engine-specific replacement
    pause_ms: int = 0      # Pause duration in milliseconds
    description: str = ""  # Human-readable description

    def to_dict(self) -> Dict:
        return {
            "pattern": self.pattern,
            "replacement": self.replacement,
            "pause_ms": self.pause_ms,
            "description": self.description,
        }


@dataclass
class VoiceConfig:
    """Configuration for a specific voice."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    persona: VoicePersona = VoicePersona.NEUTRAL
    engine: TTSEngine = TTSEngine.KOKORO
    voice_id: str = ""              # Engine-specific voice ID
    reference_audio_url: str = ""   # For cloning engines
    reference_text: str = ""        # Text matching reference audio
    emotion: EmotionStyle = EmotionStyle.NEUTRAL
    pitch: float = 1.0              # 0.5 to 2.0
    speed: float = 1.0              # 0.5 to 2.0
    punctuation_rules: List[PunctuationRule] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and clamp pitch/speed to valid ranges."""
        self.pitch = max(0.5, min(2.0, self.pitch))
        self.speed = max(0.5, min(2.0, self.speed))

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "persona": self.persona.value,
            "engine": self.engine.value,
            "voice_id": self.voice_id,
            "reference_audio_url": self.reference_audio_url,
            "reference_text": self.reference_text,
            "emotion": self.emotion.value,
            "pitch": self.pitch,
            "speed": self.speed,
            "punctuation_rules": [r.to_dict() for r in self.punctuation_rules],
            "metadata": self.metadata,
        }


@dataclass
class TTSRequest:
    """Request for TTS synthesis."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    voice_config: Optional[VoiceConfig] = None
    persona: VoicePersona = VoicePersona.NEUTRAL
    engine: Optional[TTSEngine] = None
    output_format: str = "mp3"  # mp3, wav, ogg
    sample_rate: int = 24000
    streaming: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "text": self.text,
            "voice_config": self.voice_config.to_dict() if self.voice_config else None,
            "persona": self.persona.value,
            "engine": self.engine.value if self.engine else None,
            "output_format": self.output_format,
            "sample_rate": self.sample_rate,
            "streaming": self.streaming,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class TTSResult:
    """Result of TTS synthesis."""
    request_id: str
    audio_url: str = ""             # URL to generated audio
    audio_data: Optional[bytes] = None  # Raw audio bytes (if not streaming)
    duration_ms: int = 0            # Audio duration
    character_count: int = 0
    processing_time_ms: int = 0
    engine_used: TTSEngine = TTSEngine.KOKORO
    completed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "audio_url": self.audio_url,
            "has_audio_data": self.audio_data is not None,
            "duration_ms": self.duration_ms,
            "character_count": self.character_count,
            "processing_time_ms": self.processing_time_ms,
            "engine_used": self.engine_used.value,
            "completed_at": self.completed_at,
            "error": self.error,
        }


@dataclass
class MultiSpeakerSegment:
    """A segment in multi-speaker TTS."""
    speaker: VoicePersona
    text: str
    voice_config: Optional[VoiceConfig] = None

    def to_dict(self) -> Dict:
        return {
            "speaker": self.speaker.value,
            "text": self.text,
            "voice_config": self.voice_config.to_dict() if self.voice_config else None,
        }


@dataclass
class MultiSpeakerRequest:
    """Request for multi-speaker TTS (podcast mode)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    segments: List[MultiSpeakerSegment] = field(default_factory=list)
    output_format: str = "mp3"
    sample_rate: int = 24000
    crossfade_ms: int = 100  # Crossfade between segments
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "segments": [s.to_dict() for s in self.segments],
            "output_format": self.output_format,
            "sample_rate": self.sample_rate,
            "crossfade_ms": self.crossfade_ms,
            "created_at": self.created_at,
        }


def _default_punctuation_rules() -> List[PunctuationRule]:
    """Create fresh punctuation rules to avoid sharing mutable state."""
    return [
        PunctuationRule(
            pattern="...",
            replacement="<break time='600ms'/>",
            pause_ms=600,
            description="Long pause (approx 600ms)",
        ),
        PunctuationRule(
            pattern="—",
            replacement="<break time='300ms'/>",
            pause_ms=300,
            description="Sharp break/Tone shift",
        ),
        PunctuationRule(
            pattern=",",
            replacement="<break time='150ms'/>",
            pause_ms=150,
            description="Short breath",
        ),
    ]


# Default punctuation rules for KOKORO (Host persona)
# Use _default_punctuation_rules() to get a fresh copy
DEFAULT_PUNCTUATION_RULES = _default_punctuation_rules()


def _create_default_voices() -> Dict[VoicePersona, VoiceConfig]:
    """Create fresh default voice configurations to avoid sharing mutable state."""
    return {
        VoicePersona.HOST: VoiceConfig(
            name="PMOVES Host",
            persona=VoicePersona.HOST,
            engine=TTSEngine.KOKORO,
            emotion=EmotionStyle.WARM,
            speed=0.95,
            punctuation_rules=_default_punctuation_rules(),
        ),
        VoicePersona.ARCHITECT: VoiceConfig(
            name="PMOVES Architect",
            persona=VoicePersona.ARCHITECT,
            engine=TTSEngine.FISH_SPEECH,
            emotion=EmotionStyle.EXCITED,
            speed=1.2,
            reference_text="This is the fastest CPU we have ever tested and it is absolutely mind blowing.",
        ),
        VoicePersona.OPS: VoiceConfig(
            name="PMOVES Ops",
            persona=VoicePersona.OPS,
            engine=TTSEngine.INDEXTTS2,
            emotion=EmotionStyle.AUTHORITATIVE,
            pitch=0.9,
            speed=0.9,
        ),
    }


# Default voice configurations for PMOVES.AI personas
# Use _create_default_voices() to get a fresh copy in service initialization
DEFAULT_VOICES = _create_default_voices()
