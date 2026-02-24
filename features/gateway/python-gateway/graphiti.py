"""
Agent Graphiti NATS emission for PMOVES.AI agent trail system.

Emits `agent.graphiti.signed.v1` NATS events conforming to
pmoves/contracts/schemas/agent-graphiti/signature.v1.schema.json.

This is the first service to emit graphiti events — wired into the
BoTZ MCP Gateway's tool call path for fire-and-forget trail emission.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://nats:pmoves@nats:4222")
GRAPHITI_SUBJECT = "agent.graphiti.signed.v1"

# BoTZ Gateway identity (matches pmoves/config/agent_signatures.yaml)
AGENT_ID = "botz-mcp-gateway"
DISPLAY_NAME = "BoTZ MCP Gateway"
GLYPH = "\u25A0"       # Black Square — inherits from BoTZ/Codex lineage
COLOR = "#2563EB"       # Royal Blue
VOICE = "terse"


async def emit_graphiti_signature(
    phase: str,
    summary: str,
    resonance: List[str],
    done: Optional[List[str]] = None,
    remaining: Optional[List[str]] = None,
    for_next_agent: Optional[List[str]] = None,
) -> bool:
    """Emit an agent.graphiti.signed.v1 NATS event.

    Args:
        phase: Project phase identifier (e.g., "tool-call", "startup").
        summary: One-line summary of the work (max 200 chars per schema).
        resonance: Strength domains activated.
        done: Completed items for handoff context.
        remaining: Items left behind.
        for_next_agent: Guidance for next contributor.

    Returns:
        True if event was published successfully.
    """
    try:
        import nats as nats_pkg

        nc = nats_pkg.NATS()
        await nc.connect(NATS_URL, connect_timeout=5)

        payload = {
            "agent_id": AGENT_ID,
            "display_name": DISPLAY_NAME,
            "glyph": GLYPH,
            "color": COLOR,
            "voice": VOICE,
            "phase": phase,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "resonance": resonance,
            "summary": summary,
            "handoff": {
                "done": done or [],
                "remaining": remaining or [],
                "for_next_agent": for_next_agent or [],
            },
        }

        await nc.publish(GRAPHITI_SUBJECT, json.dumps(payload).encode())
        await nc.close()
        logger.info("Emitted graphiti signature: %s", summary)
        return True
    except Exception as e:
        logger.warning("Failed to emit graphiti event: %s", e)
        return False


def emit_tool_call_trail(tool_name: str, agent_id: str, success: bool) -> None:
    """Fire-and-forget graphiti event for a gateway tool call.

    Called from gateway.py after /call and /mcp:tools/call responses.
    Never blocks the HTTP response — uses create_task if a loop is running,
    otherwise silently skips.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_emit_tool_trail(tool_name, agent_id, success))
        else:
            asyncio.run(_emit_tool_trail(tool_name, agent_id, success))
    except Exception:
        pass  # Best-effort, never block the request


async def _emit_tool_trail(tool_name: str, agent_id: str, success: bool) -> None:
    """Async tool call trail emission."""
    status = "success" if success else "error"
    await emit_graphiti_signature(
        phase="tool-call",
        summary=f"Gateway routed {tool_name} for {agent_id} ({status})",
        resonance=["mcp-routing", "tool-execution"],
        done=[f"{tool_name} → {status}"],
    )
