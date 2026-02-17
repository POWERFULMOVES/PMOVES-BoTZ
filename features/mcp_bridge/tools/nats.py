"""
NATS MCP Tools

MCP tools for NATS message bus operations:
- nats_publish: Publish event to a subject
- nats_request: Request-reply pattern
- nats_subscribe: Subscribe to subjects (returns recent messages)
- nats_stream_info: JetStream stream information

Usage:
    from pmoves_botz.features.mcp_bridge.tools.nats import TOOLS, handle_tool

    result = await handle_tool("nats_publish", {
        "subject": "research.request.v1",
        "payload": {"query": "test"}
    })
"""

import json
import os
from datetime import datetime
from typing import Any, Optional

try:
    import nats
    from nats.aio.client import Client as NATSClient
    HAS_NATS = True
except ImportError:
    HAS_NATS = False
    NATSClient = None

NATS_URL = os.getenv("NATS_URL", "nats://nats:pmoves@localhost:4222")


# Tool definitions
TOOLS = [
    {
        "name": "nats_publish",
        "description": "Publish an event to a NATS subject",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "NATS subject to publish to (e.g., 'research.request.v1')",
                },
                "payload": {
                    "type": "object",
                    "description": "JSON payload to publish",
                },
            },
            "required": ["subject", "payload"],
        },
    },
    {
        "name": "nats_request",
        "description": "Send a request and wait for a response (request-reply pattern)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Subject to send request to",
                },
                "payload": {
                    "type": "object",
                    "description": "Request payload",
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds",
                    "default": 30,
                },
            },
            "required": ["subject", "payload"],
        },
    },
    {
        "name": "nats_subjects",
        "description": "List common PMOVES NATS subjects and their purposes",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category: research, ingest, agent, botz, all",
                    "default": "all",
                },
            },
        },
    },
    {
        "name": "nats_health",
        "description": "Check NATS server connection status",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# PMOVES subject catalog
SUBJECT_CATALOG = {
    "research": {
        "research.deepresearch.request.v1": "Request LLM-based research planning",
        "research.deepresearch.result.v1": "Research results from DeepResearch",
        "supaserch.request.v1": "Request multimodal holographic research",
        "supaserch.result.v1": "SupaSerch research results",
    },
    "ingest": {
        "ingest.file.added.v1": "New file ingested to MinIO",
        "ingest.transcript.ready.v1": "Transcript completed",
        "ingest.summary.ready.v1": "Summary generated",
        "ingest.chapters.ready.v1": "Chapter markers created",
    },
    "agent": {
        "agent.tool.pre.v1": "Before tool execution",
        "agent.tool.post.v1": "After tool execution",
        "agent.handoff.request.v1": "Task delegation request",
        "agent.handoff.completed.v1": "Task delegation completed",
    },
    "botz": {
        "botz.agent.heartbeat.v1": "Agent presence heartbeat",
        "botz.work.available.v1": "Broadcast available work",
        "botz.work.claimed.v1": "Work item claimed",
        "botz.work.completed.v1": "Work completed with result",
    },
}


async def handle_tool(name: str, arguments: dict) -> dict:
    """
    Handle tool invocation.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result as MCP content block
    """
    if name == "nats_subjects":
        return _handle_subjects(arguments)

    if not HAS_NATS:
        return {"content": [{"type": "text", "text": "Error: nats-py not installed"}]}

    try:
        if name == "nats_publish":
            return await _handle_publish(arguments)
        elif name == "nats_request":
            return await _handle_request(arguments)
        elif name == "nats_health":
            return await _handle_health()
        else:
            return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


async def _handle_publish(args: dict) -> dict:
    """Handle nats_publish tool."""
    client = await nats.connect(NATS_URL)
    try:
        payload = args["payload"]
        if "timestamp" not in payload:
            payload["timestamp"] = datetime.utcnow().isoformat() + "Z"

        await client.publish(
            args["subject"],
            json.dumps(payload).encode(),
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Published to {args['subject']}",
                }
            ]
        }
    finally:
        await client.close()


async def _handle_request(args: dict) -> dict:
    """Handle nats_request tool."""
    client = await nats.connect(NATS_URL)
    try:
        payload = args["payload"]
        if "timestamp" not in payload:
            payload["timestamp"] = datetime.utcnow().isoformat() + "Z"

        timeout = args.get("timeout", 30)

        response = await client.request(
            args["subject"],
            json.dumps(payload).encode(),
            timeout=timeout,
        )

        try:
            response_data = json.loads(response.data.decode())
        except json.JSONDecodeError:
            response_data = response.data.decode()

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(response_data, indent=2),
                }
            ]
        }
    finally:
        await client.close()


async def _handle_health() -> dict:
    """Handle nats_health tool."""
    try:
        client = await nats.connect(NATS_URL, connect_timeout=5)
        await client.close()
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"NATS Status: healthy (connected to {NATS_URL})",
                }
            ]
        }
    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"NATS Status: offline ({str(e)})",
                }
            ]
        }


def _handle_subjects(args: dict) -> dict:
    """Handle nats_subjects tool."""
    category = args.get("category", "all")
    output_lines = ["PMOVES NATS Subjects:", ""]

    if category == "all":
        categories = SUBJECT_CATALOG.keys()
    else:
        categories = [category] if category in SUBJECT_CATALOG else []

    for cat in categories:
        output_lines.append(f"## {cat.upper()}")
        for subject, description in SUBJECT_CATALOG.get(cat, {}).items():
            output_lines.append(f"  {subject}")
            output_lines.append(f"    {description}")
        output_lines.append("")

    if not categories:
        output_lines.append(f"Unknown category: {category}")
        output_lines.append(f"Available: {', '.join(SUBJECT_CATALOG.keys())}")

    return {
        "content": [
            {
                "type": "text",
                "text": "\n".join(output_lines),
            }
        ]
    }
