# TTS Skill - Text-to-Speech Synthesis

**Slice:** `slices/tts/`
**Type:** Voice Synthesis Service

## Purpose

Text-to-speech synthesis with voice personas for PMOVES.AI content. Use this skill when:
- Generating audio narration from text
- Creating multi-speaker podcast content
- Applying punctuation engineering for prosody control

## Voice Personas

| Persona | Engine | Style | Use Case |
|---------|--------|-------|----------|
| HOST | Kokoro | Warm, natural flow | Introductions, narration |
| ARCHITECT | Fish Speech | Fast, excited tech jargon | Technical explanations |
| OPS | IndexTTS2 | Gritty, authoritative | Infrastructure descriptions |
| NEUTRAL | Any | Default voice | General content |

## Components

### 1. Simple Synthesis

```python
from slices.tts import TTSService, VoicePersona

# Create service
service = TTSService(http_client=client)

# Synthesize with persona
result = await service.synthesize(
    text="Welcome to PMOVES.AI",
    persona=VoicePersona.HOST,
)

print(f"Audio URL: {result.audio_url}")
print(f"Duration: {result.duration_ms}ms")
```

### 2. Punctuation Engineering

KOKORO engine supports punctuation engineering for prosody control:

| Pattern | Effect | Duration |
|---------|--------|----------|
| `...` | Long pause | ~600ms |
| `—` | Sharp break/tone shift | ~300ms |
| `,` | Short breath | ~150ms |

```python
# Punctuation engineering applied automatically for HOST persona
text = """
Imagine a world where your local hardware isn't just a server...
but a living organism.

We are looking at the P-MOVES dot A-I orchestration mesh.
It's a distributed architecture—one that mirrors high-end
production environments—but it lives entirely on your local metal.
"""

result = await service.synthesize(text, persona=VoicePersona.HOST)
```

### 3. Reference Audio Cloning

FISH_SPEECH engine supports voice cloning from reference audio:

```python
from slices.tts import VoiceConfig, TTSEngine

# Configure with reference audio
config = VoiceConfig(
    engine=TTSEngine.FISH_SPEECH,
    reference_audio_url="https://example.com/reference.mp3",
    reference_text="This is the fastest CPU we have ever tested.",
    speed=1.2,
)

result = await service.synthesize(
    text="This is not just storage—this is Local Inference!",
    voice_config=config,
)
```

### 4. Emotion Prompts

INDEXTTS2 engine supports natural language style prompts:

```python
from slices.tts import VoiceConfig, TTSEngine, EmotionStyle

# Configure with emotion
config = VoiceConfig(
    engine=TTSEngine.INDEXTTS2,
    emotion=EmotionStyle.WHISPER,
    pitch=0.8,
    speed=0.7,
)

result = await service.synthesize(
    text="And it learns. The Evo-Controller reads those packets...",
    voice_config=config,
)
```

### 5. Multi-Speaker Podcast Mode

Generate conversations with multiple voice personas:

```python
from slices.tts import MultiSpeakerSegment

segments = [
    MultiSpeakerSegment(
        speaker=VoicePersona.HOST,
        text="Imagine a world where your local hardware is a living organism.",
    ),
    MultiSpeakerSegment(
        speaker=VoicePersona.OPS,
        text="It starts with Local-First Infrastructure. We aren't renting power.",
    ),
    MultiSpeakerSegment(
        speaker=VoicePersona.ARCHITECT,
        text="Correct! And this is not just storage—this is Local Inference!",
    ),
]

result = await service.synthesize_multi_speaker(
    segments=segments,
    crossfade_ms=100,
)
```

## Engine Configuration

| Engine | URL | API Key Required |
|--------|-----|------------------|
| Kokoro | `http://localhost:8090` | No |
| Fish Speech | `http://localhost:8091` | No |
| IndexTTS2 | `http://localhost:8092` | No |
| ElevenLabs | Cloud API | Yes |
| OpenAI TTS | Cloud API | Yes |

```python
service = TTSService(
    http_client=client,
    kokoro_url="http://localhost:8090",
    fish_speech_url="http://localhost:8091",
    indextts_url="http://localhost:8092",
    elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY"),
    openai_api_key=os.environ.get("OPENAI_API_KEY"),
)
```

## Integration with Discord Bot

```python
# In Discord bot command handler
@bot.tree.command(name="speak", description="Generate speech from text")
async def speak_cmd(
    interaction: discord.Interaction,
    text: str,
    persona: str = "host",
):
    await interaction.response.defer()

    tts_service = TTSService(http_client=httpx.AsyncClient())
    persona_enum = VoicePersona(persona.lower())

    result = await tts_service.synthesize(text, persona=persona_enum)

    if result.error:
        await interaction.followup.send(f"TTS failed: {result.error}")
    else:
        await interaction.followup.send(f"Audio: {result.audio_url}")
```

## References

- docs/agents/PMOVES_Engine_Templates.md - TTS template specifications
- Kokoro TTS documentation
- Fish Speech documentation
- IndexTTS2 documentation
