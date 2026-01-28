"""
A2A Protocol Type Definitions.

Defines the core data structures for Agent-to-Agent communication:
- AgentCard: Agent identity and capability discovery
- Task: Stateful unit of work with lifecycle management
- Messages and Artifacts: Communication primitives

Reference: https://github.com/google/A2A (conceptual)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class TaskState(Enum):
    """A2A Task lifecycle states."""
    SUBMITTED = "submitted"      # Task received but not started
    WORKING = "working"          # Agent actively processing
    INPUT_REQUIRED = "input-required"  # Needs clarification/approval
    COMPLETED = "completed"      # Task finished successfully
    FAILED = "failed"            # Unrecoverable error
    CANCELLED = "cancelled"      # Cancelled by client


@dataclass
class AgentCapability:
    """High-level capability of an agent."""
    name: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentSkill:
    """Granular skill definition for A2A discovery."""
    id: str
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentCard:
    """
    Agent Card - The A2A identity and capability statement.

    Hosted at /.well-known/agent.json for dynamic discovery.
    """
    name: str
    description: str
    version: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    skills: List[AgentSkill] = field(default_factory=list)
    input_modalities: List[str] = field(default_factory=lambda: ["text/plain", "application/json"])
    output_modalities: List[str] = field(default_factory=lambda: ["text/plain", "application/json", "text/markdown"])
    authentication: Dict[str, Any] = field(default_factory=lambda: {"type": "none"})
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "skills": [s.to_dict() for s in self.skills],
            "input_modalities": self.input_modalities,
            "output_modalities": self.output_modalities,
            "authentication": self.authentication,
            "metadata": self.metadata,
        }


@dataclass
class TaskArtifact:
    """Output artifact from a completed task."""
    type: str  # "text", "code", "file", "json"
    content: Any
    name: Optional[str] = None
    mime_type: str = "text/plain"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskMessage:
    """Message within a task context."""
    role: str  # "user", "agent", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    parts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Task:
    """
    A2A Task - The fundamental unit of agent work.

    Supports the full A2A lifecycle:
    submitted -> working -> [input-required] -> completed/failed
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: TaskState = TaskState.SUBMITTED
    skill_id: Optional[str] = None
    messages: List[TaskMessage] = field(default_factory=list)
    artifacts: List[TaskArtifact] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "state": self.state.value,
            "skill_id": self.skill_id,
            "messages": [m.to_dict() for m in self.messages],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "error": self.error,
        }

    def update_state(self, new_state: TaskState) -> None:
        """Update task state with timestamp."""
        self.state = new_state
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def add_message(self, role: str, content: str) -> TaskMessage:
        """Add a message to the task."""
        msg = TaskMessage(role=role, content=content)
        self.messages.append(msg)
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        return msg

    def add_artifact(self, artifact_type: str, content: Any, name: Optional[str] = None) -> TaskArtifact:
        """Add an artifact to the task."""
        artifact = TaskArtifact(type=artifact_type, content=content, name=name)
        self.artifacts.append(artifact)
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        return artifact

    def complete(self, result: Any = None) -> None:
        """Mark task as completed with optional result artifact."""
        if result is not None:
            self.add_artifact("result", result)
        self.update_state(TaskState.COMPLETED)

    def fail(self, error: str) -> None:
        """Mark task as failed with error message."""
        self.error = error
        self.update_state(TaskState.FAILED)
