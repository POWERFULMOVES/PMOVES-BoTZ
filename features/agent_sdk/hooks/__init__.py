"""
PMOVES Agent SDK Hooks

Observability hooks for agent execution:
- Audit: Log all tool usage for security and debugging
- NATS Publisher: Publish events for multi-agent coordination
- Cost Tracker: Track token usage and API costs

Hooks fire at key points:
- PreToolUse: Before tool execution
- PostToolUse: After tool execution

Usage with Claude Agent SDK:
    options = ClaudeAgentOptions(
        hooks={
            "PreToolUse": [{"matcher": {"tool_name": "*"}, "hooks": [...]}],
            "PostToolUse": [{"matcher": {"tool_name": "*"}, "hooks": [...]}],
        }
    )
"""

from .audit import AuditHook, audit_tool_use
from .nats_publisher import NATSPublisherHook, publish_tool_event
from .cost_tracker import CostTrackerHook, track_cost

__all__ = [
    "AuditHook",
    "audit_tool_use",
    "NATSPublisherHook",
    "publish_tool_event",
    "CostTrackerHook",
    "track_cost",
]
