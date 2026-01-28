"""
A2A Slice - Agent-to-Agent Protocol Integration.

This vertical slice provides A2A protocol access for the Agent SDK:
- api.py: A2A endpoints for SDK agents
- service.py: A2A client wrapper
- models.py: Re-exports from gateway A2A module
- SKILL.md: Agent context for A2A tasks

Wraps the gateway's A2A module for use by SDK agents.

Use: from slices.a2a import A2AService
"""

# Re-export types from gateway A2A module
import sys
from pathlib import Path

# Add gateway path for imports
gateway_path = Path(__file__).parent.parent.parent.parent / "gateway" / "python-gateway"
if str(gateway_path) not in sys.path:
    sys.path.insert(0, str(gateway_path))

try:
    from a2a import (
        AgentCard,
        AgentCapability,
        AgentSkill,
        Task,
        TaskState,
        TaskMessage,
        TaskArtifact,
        A2AClient,
        RemoteAgent,
        execute_remote_task,
    )
    A2A_AVAILABLE = True
except ImportError:
    A2A_AVAILABLE = False
    # Stub types
    AgentCard = None
    A2AClient = None
    Task = None
    TaskState = None

from .service import A2AService
from .. import register_slice

# Register this slice
register_slice("a2a")(A2AService)

__all__ = [
    "A2AService",
    "A2A_AVAILABLE",
    # Re-exported types
    "AgentCard",
    "AgentCapability",
    "AgentSkill",
    "Task",
    "TaskState",
    "TaskMessage",
    "TaskArtifact",
    "A2AClient",
    "RemoteAgent",
    "execute_remote_task",
]
