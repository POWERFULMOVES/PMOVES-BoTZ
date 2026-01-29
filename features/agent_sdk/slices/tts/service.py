"""
TTS Slice - Service Layer.

Orchestrates text-to-speech synthesis:
- Routes to appropriate TTS engine based on persona
- Applies punctuation engineering rules
- Supports multi-speaker podcast mode
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

from .models import (
    _create_default_voices,
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

logger = logging.getLogger(__name__)


class TTSService:
    """
    TTS Service - Text-to-speech synthesis with voice personas.

    This service encapsulates all TTS operations in a single vertical slice.

    Usage:
        service = TTSService(http_client=client)

        # Simple synthesis
        result = await service.synthesize(
            text="Welcome to PMOVES.AI",
            persona=VoicePersona.HOST,
        )

        # Multi-speaker podcast
        result = await service.synthesize_multi_speaker([
            MultiSpeakerSegment(VoicePersona.HOST, "Welcome to the show."),
            MultiSpeakerSegment(VoicePersona.ARCHITECT, "Let's talk tech!"),
        ])
    """

    def __init__(
        self,
        http_client: Optional[Any] = None,
        kokoro_url: str = "http://localhost:8090",
        fish_speech_url: str = "http://localhost:8091",
        indextts_url: str = "http://localhost:8092",
        vibevoice_url: str = "http://localhost:8093",
        elevenlabs_api_key: str = "",
        openai_api_key: str = "",
    ):
        """
        Initialize TTS Service.

        Args:
            http_client: Async HTTP client
            kokoro_url: Kokoro TTS service URL
            fish_speech_url: Fish Speech service URL
            indextts_url: IndexTTS2 service URL
            vibevoice_url: VibeVoice multi-speaker service URL
            elevenlabs_api_key: ElevenLabs API key
            openai_api_key: OpenAI API key for TTS
        """
        self.http_client = http_client
        self.engine_urls = {
            TTSEngine.KOKORO: kokoro_url,
            TTSEngine.FISH_SPEECH: fish_speech_url,
            TTSEngine.INDEXTTS2: indextts_url,
            TTSEngine.VIBEVOICE: vibevoice_url,
        }
        self.elevenlabs_api_key = elevenlabs_api_key
        self.openai_api_key = openai_api_key

        # Voice configurations (can be customized)
        # Use factory function to get fresh copies, avoiding shared mutable state
        self.voices: Dict[VoicePersona, VoiceConfig] = _create_default_voices()

    async def synthesize(
        self,
        text: str,
        persona: VoicePersona = VoicePersona.NEUTRAL,
        voice_config: Optional[VoiceConfig] = None,
        engine: Optional[TTSEngine] = None,
        output_format: str = "mp3",
    ) -> TTSResult:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            persona: Voice persona to use
            voice_config: Custom voice configuration (overrides persona)
            engine: Force specific engine (overrides persona default)
            output_format: Output format (mp3, wav, ogg)

        Returns:
            TTSResult with audio URL or data
        """
        start_time = time.time()

        # Get voice configuration
        config = voice_config or self.voices.get(persona, self.voices[VoicePersona.HOST])

        # Determine engine
        tts_engine = engine or config.engine

        # Apply punctuation engineering
        processed_text = self._apply_punctuation_rules(text, config.punctuation_rules)

        request = TTSRequest(
            text=processed_text,
            voice_config=config,
            persona=persona,
            engine=tts_engine,
            output_format=output_format,
        )

        logger.info(f"TTS request {request.id}: {len(text)} chars via {tts_engine.value}")

        try:
            # Route to appropriate engine
            if tts_engine == TTSEngine.KOKORO:
                result = await self._synthesize_kokoro(request)
            elif tts_engine == TTSEngine.FISH_SPEECH:
                result = await self._synthesize_fish_speech(request)
            elif tts_engine == TTSEngine.INDEXTTS2:
                result = await self._synthesize_indextts(request)
            elif tts_engine == TTSEngine.ELEVENLABS:
                result = await self._synthesize_elevenlabs(request)
            elif tts_engine == TTSEngine.OPENAI:
                result = await self._synthesize_openai(request)
            else:
                result = TTSResult(
                    request_id=request.id,
                    engine_used=tts_engine,
                    error=f"Unsupported engine: {tts_engine}",
                )

            result.processing_time_ms = int((time.time() - start_time) * 1000)
            result.character_count = len(text)
            return result

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return TTSResult(
                request_id=request.id,
                error=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    async def synthesize_multi_speaker(
        self,
        segments: List[MultiSpeakerSegment],
        output_format: str = "mp3",
        crossfade_ms: int = 100,
    ) -> TTSResult:
        """
        Synthesize multi-speaker content (podcast mode).

        Args:
            segments: List of speaker segments
            output_format: Output format
            crossfade_ms: Crossfade duration between segments

        Returns:
            TTSResult with combined audio
        """
        start_time = time.time()

        request = MultiSpeakerRequest(
            segments=segments,
            output_format=output_format,
            crossfade_ms=crossfade_ms,
        )

        logger.info(f"Multi-speaker TTS request {request.id}: {len(segments)} segments")

        if not segments:
            return TTSResult(
                request_id=request.id,
                engine_used=TTSEngine.VIBEVOICE,
                error="No segments provided for multi-speaker synthesis",
            )

        if not self.http_client:
            return TTSResult(
                request_id=request.id,
                error="HTTP client not configured",
            )

        try:
            # Use VibeVoice engine for multi-speaker synthesis
            vibevoice_url = self.engine_urls.get(TTSEngine.VIBEVOICE)
            if not vibevoice_url:
                return TTSResult(
                    request_id=request.id,
                    error="VIBEVOICE engine URL not configured",
                )

            response = await self.http_client.post(
                f"{vibevoice_url}/multi-speaker",
                json=request.to_dict(),
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            return TTSResult(
                request_id=request.id,
                audio_url=data.get("audio_url", ""),
                duration_ms=data.get("duration_ms", 0),
                character_count=sum(len(s.text) for s in segments),
                engine_used=TTSEngine.VIBEVOICE,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.error(f"Multi-speaker TTS failed: {e}")
            return TTSResult(
                request_id=request.id,
                error=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    def _apply_punctuation_rules(
        self,
        text: str,
        rules: List[PunctuationRule],
    ) -> str:
        """Apply punctuation engineering rules to text."""
        if not rules:
            return text

        result = text
        for rule in rules:
            result = result.replace(rule.pattern, rule.replacement)

        return result

    async def _synthesize_kokoro(self, request: TTSRequest) -> TTSResult:
        """Synthesize using Kokoro TTS (natural flow)."""
        if not self.http_client:
            return TTSResult(request_id=request.id, error="HTTP client not configured")

        try:
            response = await self.http_client.post(
                f"{self.engine_urls[TTSEngine.KOKORO]}/synthesize",
                json={
                    "text": request.text,
                    "voice_id": request.voice_config.voice_id if request.voice_config else "",
                    "speed": request.voice_config.speed if request.voice_config else 1.0,
                    "format": request.output_format,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            return TTSResult(
                request_id=request.id,
                audio_url=data.get("audio_url", ""),
                duration_ms=data.get("duration_ms", 0),
                engine_used=TTSEngine.KOKORO,
            )

        except Exception as e:
            return TTSResult(request_id=request.id, error=str(e))

    async def _synthesize_fish_speech(self, request: TTSRequest) -> TTSResult:
        """Synthesize using Fish Speech (reference audio cloning)."""
        if not self.http_client:
            return TTSResult(request_id=request.id, error="HTTP client not configured")

        config = request.voice_config
        try:
            response = await self.http_client.post(
                f"{self.engine_urls[TTSEngine.FISH_SPEECH]}/synthesize",
                json={
                    "text": request.text,
                    "reference_audio": config.reference_audio_url if config else "",
                    "reference_text": config.reference_text if config else "",
                    "speed": config.speed if config else 1.0,
                    "format": request.output_format,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            return TTSResult(
                request_id=request.id,
                audio_url=data.get("audio_url", ""),
                duration_ms=data.get("duration_ms", 0),
                engine_used=TTSEngine.FISH_SPEECH,
            )

        except Exception as e:
            return TTSResult(request_id=request.id, error=str(e))

    async def _synthesize_indextts(self, request: TTSRequest) -> TTSResult:
        """Synthesize using IndexTTS2 (emotion prompts)."""
        if not self.http_client:
            return TTSResult(request_id=request.id, error="HTTP client not configured")

        config = request.voice_config
        try:
            # Build emotion/style prompt
            style_prompt = self._build_style_prompt(config) if config else ""

            response = await self.http_client.post(
                f"{self.engine_urls[TTSEngine.INDEXTTS2]}/synthesize",
                json={
                    "text": request.text,
                    "style_prompt": style_prompt,
                    "pitch": config.pitch if config else 1.0,
                    "speed": config.speed if config else 1.0,
                    "format": request.output_format,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            return TTSResult(
                request_id=request.id,
                audio_url=data.get("audio_url", ""),
                duration_ms=data.get("duration_ms", 0),
                engine_used=TTSEngine.INDEXTTS2,
            )

        except Exception as e:
            return TTSResult(request_id=request.id, error=str(e))

    async def _synthesize_elevenlabs(self, request: TTSRequest) -> TTSResult:
        """Synthesize using ElevenLabs API."""
        if not self.http_client or not self.elevenlabs_api_key:
            return TTSResult(
                request_id=request.id,
                error="ElevenLabs not configured",
            )

        config = request.voice_config
        voice_id = config.voice_id if config else "21m00Tcm4TlvDq8ikWAM"  # Default voice

        try:
            response = await self.http_client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.elevenlabs_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": request.text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
                timeout=60.0,
            )
            response.raise_for_status()

            return TTSResult(
                request_id=request.id,
                audio_data=response.content,
                engine_used=TTSEngine.ELEVENLABS,
            )

        except Exception as e:
            return TTSResult(request_id=request.id, error=str(e))

    async def _synthesize_openai(self, request: TTSRequest) -> TTSResult:
        """Synthesize using OpenAI TTS API."""
        if not self.http_client or not self.openai_api_key:
            return TTSResult(
                request_id=request.id,
                error="OpenAI TTS not configured",
            )

        try:
            response = await self.http_client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "tts-1",
                    "input": request.text,
                    "voice": "alloy",
                    "response_format": request.output_format,
                },
                timeout=60.0,
            )
            response.raise_for_status()

            return TTSResult(
                request_id=request.id,
                audio_data=response.content,
                engine_used=TTSEngine.OPENAI,
            )

        except Exception as e:
            return TTSResult(request_id=request.id, error=str(e))

    def _build_style_prompt(self, config: VoiceConfig) -> str:
        """Build style/emotion prompt for IndexTTS2."""
        parts = []

        if config.pitch < 1.0:
            parts.append("Low pitch")
        elif config.pitch > 1.0:
            parts.append("High pitch")
        else:
            parts.append("Normal pitch")

        if config.speed < 1.0:
            parts.append("slow speed")
        elif config.speed > 1.0:
            parts.append("fast speed")

        if config.emotion == EmotionStyle.AUTHORITATIVE:
            parts.append("authoritative")
        elif config.emotion == EmotionStyle.EXCITED:
            parts.append("excited")
        elif config.emotion == EmotionStyle.WHISPER:
            parts.append("whisper")
        elif config.emotion == EmotionStyle.SERIOUS:
            parts.append("serious")
        elif config.emotion == EmotionStyle.WARM:
            parts.append("warm")

        return ", ".join(parts)

    def configure_voice(
        self,
        persona: VoicePersona,
        config: VoiceConfig,
    ) -> None:
        """Configure a voice persona."""
        self.voices[persona] = config
        logger.info(f"Configured voice persona: {persona.value}")

    def get_voice_config(self, persona: VoicePersona) -> Optional[VoiceConfig]:
        """Get configuration for a voice persona."""
        return self.voices.get(persona)

    def list_voices(self) -> Dict[str, Dict]:
        """List all configured voices."""
        return {
            persona.value: config.to_dict()
            for persona, config in self.voices.items()
        }
