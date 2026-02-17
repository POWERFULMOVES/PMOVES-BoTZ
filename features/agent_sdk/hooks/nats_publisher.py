"""
NATS Publisher Hook

Publishes tool execution events to NATS for multi-agent coordination.
Enables other agents to react to tool usage in real-time.

Events Published:
- agent.tool.pre.v1: Before tool execution
- agent.tool.post.v1: After tool execution
- botz.work.progress.v1: Task progress updates

Usage:
    # As a function
    await publish_tool_event(tool_name, input_data, result, agent_id)

    # As CLI (for hook command)
    python -m pmoves_botz.features.agent_sdk.hooks.nats_publisher --agent-id xxx
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Optional

try:
    import nats
    HAS_NATS = True
except ImportError:
    HAS_NATS = False


class NATSPublisherHook:
    """
    NATS publisher hook for agent coordination.

    Publishes events for:
    - Tool execution (pre/post)
    - Task progress
    - Agent status updates

    Attributes:
        agent_id: Agent identifier
        nats_url: NATS server URL
    """

    NATS_URL = os.getenv("NATS_URL", "nats://nats:pmoves@localhost:4222")

    def __init__(self, agent_id: str):
        """
        Initialize NATS publisher hook.

        Args:
            agent_id: Agent identifier
        """
        self.agent_id = agent_id
        self._client = None

    async def connect(self) -> None:
        """Connect to NATS."""
        if HAS_NATS:
            try:
                self._client = await nats.connect(self.NATS_URL)
            except Exception:
                self._client = None

    async def disconnect(self) -> None:
        """Disconnect from NATS."""
        if self._client:
            await self._client.close()
            self._client = None

    async def pre_tool_use(
        self,
        tool_name: str,
        input_data: dict,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Publish pre-tool event.

        Args:
            tool_name: Tool being called
            input_data: Tool input
            context: Execution context

        Returns:
            Empty dict
        """
        await self._publish("agent.tool.pre.v1", {
            "agent_id": self.agent_id,
            "tool_name": tool_name,
            "input_keys": list(input_data.keys()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        return {}

    async def post_tool_use(
        self,
        tool_name: str,
        input_data: dict,
        result: Any,
        duration_ms: float,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Publish post-tool event.

        Args:
            tool_name: Tool called
            input_data: Tool input
            result: Tool result
            duration_ms: Execution time
            context: Execution context

        Returns:
            Empty dict
        """
        success = not (isinstance(result, dict) and "error" in result)

        await self._publish("agent.tool.post.v1", {
            "agent_id": self.agent_id,
            "tool_name": tool_name,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        return {}

    async def publish_progress(
        self,
        task_id: str,
        progress: float,
        status: str,
        message: Optional[str] = None,
    ) -> None:
        """
        Publish task progress update.

        Args:
            task_id: Task identifier
            progress: Progress percentage (0-100)
            status: Status string
            message: Optional status message
        """
        await self._publish("botz.work.progress.v1", {
            "agent_id": self.agent_id,
            "task_id": task_id,
            "progress": progress,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    async def _publish(self, subject: str, payload: dict) -> None:
        """Publish to NATS."""
        if self._client:
            try:
                await self._client.publish(
                    subject,
                    json.dumps(payload).encode(),
                )
            except Exception:
                pass  # Don't fail on publish errors


async def publish_tool_event(
    tool_name: str,
    input_data: dict,
    result: Any,
    agent_id: str,
    duration_ms: float = 0,
) -> None:
    """
    Convenience function to publish tool event.

    Args:
        tool_name: Tool name
        input_data: Tool input
        result: Tool result
        agent_id: Agent ID
        duration_ms: Execution time
    """
    hook = NATSPublisherHook(agent_id)
    await hook.connect()
    try:
        await hook.post_tool_use(tool_name, input_data, result, duration_ms)
    finally:
        await hook.disconnect()


def main():
    """CLI entry point for hook command."""
    parser = argparse.ArgumentParser(description="PMOVES NATS Publisher Hook")
    parser.add_argument("--agent-id", required=True, help="Agent identifier")
    parser.add_argument("--tool", help="Tool name")
    parser.add_argument("--phase", choices=["pre", "post"], default="post")

    args = parser.parse_args()

    # Read input from stdin
    input_json = sys.stdin.read() if not sys.stdin.isatty() else "{}"

    try:
        data = json.loads(input_json)
    except json.JSONDecodeError:
        data = {}

    # Prepare event
    event = {
        "agent_id": args.agent_id,
        "tool_name": args.tool or data.get("tool_name", "unknown"),
        "phase": args.phase,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Synchronous NATS publish for CLI
    if HAS_NATS:
        import asyncio

        async def publish():
            try:
                client = await nats.connect(os.getenv("NATS_URL", "nats://nats:pmoves@localhost:4222"))
                subject = f"agent.tool.{args.phase}.v1"
                await client.publish(subject, json.dumps(event).encode())
                await client.close()
            except Exception:
                pass

        asyncio.run(publish())

    # Output empty JSON
    print("{}")


if __name__ == "__main__":
    main()
