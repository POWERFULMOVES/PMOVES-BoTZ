"""
Google Cast MCP Tools

MCP tools for Google Cast device management and TTS casting:
- cast_discover: Scan for Cast devices on LAN
- cast_list: List discovered Cast devices
- cast_speech: Synthesize TTS and cast to device
- cast_audio: Cast audio file to device
- cast_status: Get device status
- cast_stop: Stop playback on device

Usage:
    from pmoves_botz.features.mcp_bridge.tools.cast import TOOLS, handle_tool

    result = await handle_tool("cast_speech", {
        "text": "Hello from PMOVES",
        "device": "Brysons Speakers speaker"
    })
"""

import asyncio
import json
import os
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

ULTIMATE_TTS_URL = os.getenv("ULTIMATE_TTS_URL", "http://localhost:7861")
FLUTE_GATEWAY_URL = os.getenv("FLUTE_GATEWAY_URL", "http://localhost:8055")

# Device cache
_discovered_devices: list[dict] = []
_last_discovery: Optional[float] = None


# Tool definitions
TOOLS = [
    {
        "name": "cast_discover",
        "description": "Scan LAN for Google Cast devices (Chromecast, Nest Audio, Google Home, Android TV, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "Force rediscovery even if cache is fresh",
                    "default": False,
                },
            },
        },
    },
    {
        "name": "cast_list",
        "description": "List discovered Google Cast devices with their details",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "cast_speech",
        "description": "Synthesize text to speech and cast to Google Cast device (uses Flute-Gateway or Ultimate-TTS)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to synthesize and speak",
                },
                "device": {
                    "type": "string",
                    "description": "Cast device name (leave empty for default device)",
                },
                "voice": {
                    "type": "string",
                    "description": "TTS voice/engine (default: ultimate-tts Kokoro)",
                    "default": "Kokoro",
                },
                "use_flute": {
                    "type": "boolean",
                    "description": "Use Flute-Gateway prosodic TTS instead of Ultimate-TTS",
                    "default": False,
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "cast_audio",
        "description": "Cast an audio file to Google Cast device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path to audio file (URL or local file path)",
                },
                "device": {
                    "type": "string",
                    "description": "Cast device name (leave empty for default device)",
                },
            },
            "required": ["audio_path"],
        },
    },
    {
        "name": "cast_status",
        "description": "Get playback status from Cast device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Cast device name (leave empty for default device)",
                },
            },
        },
    },
    {
        "name": "cast_stop",
        "description": "Stop playback on Cast device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Cast device name (leave empty for default device)",
                },
            },
        },
    },
]


async def handle_tool(name: str, arguments: dict) -> dict:
    """
    Handle tool invocation.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result as MCP content block
    """
    try:
        if name == "cast_discover":
            return await _handle_discover(arguments)
        elif name == "cast_list":
            return await _handle_list()
        elif name == "cast_speech":
            return await _handle_speech(arguments)
        elif name == "cast_audio":
            return await _handle_audio(arguments)
        elif name == "cast_status":
            return await _handle_status(arguments)
        elif name == "cast_stop":
            return await _handle_stop(arguments)
        else:
            return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


async def _discover_devices(force: bool = False) -> list[dict]:
    """Discover Cast devices using catt scan."""
    global _discovered_devices, _last_discovery

    import time
    current_time = time.time()

    # Use cache if less than 5 minutes old
    if not force and _last_discovery and (current_time - _last_discovery) < 300:
        return _discovered_devices

    try:
        # Run catt scan
        proc = await asyncio.create_subprocess_exec(
            "catt", "scan",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            return []

        # Parse catt scan output
        # Format: "Device Name - 192.168.1.x:port"
        devices = []
        for line in stdout.decode().strip().split("\n"):
            if " - " in line and ":" in line:
                parts = line.split(" - ")
                if len(parts) == 2:
                    name = parts[0].strip()
                    addr_port = parts[1].strip()
                    ip = addr_port.split(":")[0] if ":" in addr_port else addr_port

                    devices.append({
                        "name": name,
                        "ip": ip,
                        "address": addr_port,
                    })

        _discovered_devices = devices
        _last_discovery = current_time
        return devices

    except FileNotFoundError:
        # catt not installed
        return []
    except Exception as e:
        return []


async def _handle_discover(args: dict) -> dict:
    """Handle cast_discover tool."""
    force = args.get("force", False)
    devices = await _discover_devices(force)

    if not devices:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "No Cast devices found. Ensure catt is installed and devices are on the same LAN.",
                }
            ]
        }

    output_lines = [f"Found {len(devices)} Cast device(s):", ""]
    for i, device in enumerate(devices, 1):
        output_lines.append(f"{i}. {device['name']}")
        output_lines.append(f"   IP: {device['ip']}")

    return {
        "content": [
            {
                "type": "text",
                "text": "\n".join(output_lines),
            }
        ]
    }


async def _handle_list() -> dict:
    """Handle cast_list tool."""
    devices = await _discover_devices()

    if not devices:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "No Cast devices discovered. Run cast_discover first.",
                }
            ]
        }

    output_lines = [f"Discovered {len(devices)} Cast device(s):", ""]
    for i, device in enumerate(devices, 1):
        output_lines.append(f"{i}. {device['name']}")
        output_lines.append(f"   IP: {device['ip']}")
        output_lines.append("")

    return {
        "content": [
            {
                "type": "text",
                "text": "\n".join(output_lines),
            }
        ]
    }


async def _synthesize_tts_flute(text: str, voice: str = "default") -> Optional[str]:
    """Synthesize TTS using Flute-Gateway prosodic API."""
    if not HAS_HTTPX:
        return None

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{FLUTE_GATEWAY_URL}/v1/voice/synthesize/prosodic",
                json={"text": text, "voice": voice},
            )
            response.raise_for_status()

            # Save audio to temp file
            audio_data = response.content
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_file.write(audio_data)
            temp_file.close()
            return temp_file.name

    except Exception as e:
        return None


async def _synthesize_tts_ultimate(text: str, engine: str = "Kokoro") -> Optional[str]:
    """Synthesize TTS using Ultimate-TTS Studio."""
    if not HAS_HTTPX:
        return None

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ULTIMATE_TTS_URL}/api/predict",
                json={"data": [text, engine, 0.5, 0.5, 0.5]},
            )
            response.raise_for_status()

            result = response.json()
            if "data" in result and len(result["data"]) > 0:
                return result["data"][0]  # Audio file path

    except Exception as e:
        pass

    return None


async def _synthesize_tts_google(text: str) -> Optional[str]:
    """Synthesize TTS using Google TTS fallback."""
    try:
        from gtts import gTTS

        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts = gTTS(text=text, lang="en")
        tts.save(temp_file.name)
        return temp_file.name

    except Exception:
        return None


async def _handle_speech(args: dict) -> dict:
    """Handle cast_speech tool."""
    text = args.get("text", "")
    device = args.get("device")
    voice = args.get("voice", "Kokoro")
    use_flute = args.get("use_flute", False)

    if not text:
        return {"content": [{"type": "text", "text": "Error: text is required"}]}

    # Try Flute-Gateway first if requested
    audio_path = None
    if use_flute:
        audio_path = await _synthesize_tts_flute(text, voice)
        if audio_path:
            return await _cast_audio_file(audio_path, device, cleanup=True)

    # Try Ultimate-TTS
    audio_path = await _synthesize_tts_ultimate(text, voice)
    if audio_path:
        return await _cast_audio_file(audio_path, device, cleanup=False)

    # Fallback to Google TTS
    audio_path = await _synthesize_tts_google(text)
    if audio_path:
        return await _cast_audio_file(audio_path, device, cleanup=True)

    return {
        "content": [
            {
                "type": "text",
                "text": "Failed to synthesize TTS. Ensure Flute-Gateway or Ultimate-TTS is running.",
            }
        ]
    }


async def _handle_audio(args: dict) -> dict:
    """Handle cast_audio tool."""
    audio_path = args.get("audio_path", "")
    device = args.get("device")

    if not audio_path:
        return {"content": [{"type": "text", "text": "Error: audio_path is required"}]}

    return await _cast_audio_file(audio_path, device, cleanup=False)


async def _cast_audio_file(
    audio_path: str, device: Optional[str], cleanup: bool
) -> dict:
    """Cast audio file to device."""
    try:
        cmd = ["catt", "cast", audio_path]
        if device:
            cmd.extend(["-d", device])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        # Cleanup temp file if needed
        if cleanup and os.path.exists(audio_path):
            os.unlink(audio_path)

        if proc.returncode == 0:
            device_name = device or "default device"
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Casted audio to {device_name}",
                    }
                ]
            }
        else:
            error_msg = stderr.decode().strip() or "Unknown error"
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Cast failed: {error_msg}",
                    }
                ]
            }

    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Cast error: {str(e)}",
                }
            ]
        }


async def _handle_status(args: dict) -> dict:
    """Handle cast_status tool."""
    device = args.get("device")

    try:
        cmd = ["catt", "status"]
        if device:
            cmd.extend(["-d", device])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode == 0:
            status_output = stdout.decode().strip()
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Device Status:\n{status_output}",
                    }
                ]
            }
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Could not get status: {stderr.decode().strip()}",
                    }
                ]
            }

    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Status error: {str(e)}",
                }
            ]
        }


async def _handle_stop(args: dict) -> dict:
    """Handle cast_stop tool."""
    device = args.get("device")

    try:
        cmd = ["catt", "stop"]
        if device:
            cmd.extend(["-d", device])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode == 0:
            device_name = device or "default device"
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Stopped playback on {device_name}",
                    }
                ]
            }
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Stop failed: {stderr.decode().strip()}",
                    }
                ]
            }

    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Stop error: {str(e)}",
                }
            ]
        }
