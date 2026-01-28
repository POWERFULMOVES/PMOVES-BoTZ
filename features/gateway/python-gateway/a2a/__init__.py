"""
A2A (Agent-to-Agent) Protocol Implementation for PMOVES-BoTZ.

This module implements the Google A2A protocol for agent interoperability:
- Agent Card discovery at /.well-known/agent.json
- JSON-RPC 2.0 task lifecycle management
- SSE streaming for real-time updates

Reference: docs/agents/AI Agent Integration and Best Practices.md
"""

from .types import (
    AgentCard,
    AgentCapability,
    AgentSkill,
    Task,
    TaskState,
    TaskMessage,
    TaskArtifact,
)
from .agent_card import get_agent_card, build_agent_card
from .task_handler import TaskHandler, TaskStore
from .client import A2AClient, RemoteAgent, execute_remote_task

__version__ = "1.0.0"
__all__ = [
    # Types
    "AgentCard",
    "AgentCapability",
    "AgentSkill",
    "Task",
    "TaskState",
    "TaskMessage",
    "TaskArtifact",
    # Server
    "get_agent_card",
    "build_agent_card",
    "TaskHandler",
    "TaskStore",
    # Client
    "A2AClient",
    "RemoteAgent",
    "execute_remote_task",
]
