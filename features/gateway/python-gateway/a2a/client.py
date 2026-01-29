"""
A2A Client - Client for calling remote A2A agents.

Provides capabilities for:
- Discovering remote agent capabilities via Agent Card
- Creating and managing tasks on remote agents
- Streaming task updates via SSE

Reference: docs/agents/AI Agent Integration and Best Practices.md (Section 5.3)
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generator, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

from .types import AgentCard, Task, TaskState, AgentCapability, AgentSkill

logger = logging.getLogger(__name__)


@dataclass
class RemoteAgent:
    """Represents a discovered remote A2A agent."""
    url: str
    card: Optional[AgentCard] = None
    discovered_at: Optional[float] = None

    @property
    def name(self) -> str:
        return self.card.name if self.card else self.url

    @property
    def capabilities(self) -> list:
        return self.card.capabilities if self.card else []


class A2AClient:
    """
    A2A Protocol Client for calling remote agents.

    Uses httpx for non-blocking HTTP requests.

    Usage:
        client = A2AClient()

        # Discover agent
        agent = client.discover("http://other-agent:7000")
        print(agent.card.capabilities)

        # Create task
        task = client.create_task(
            agent_url="http://other-agent:7000",
            skill_id="code_execution",
            message="Run pytest tests/"
        )

        # Poll for completion
        task = client.wait_for_completion(task.id, "http://other-agent:7000")
        print(task.artifacts)
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize A2A Client.

        Args:
            timeout: Default timeout for HTTP requests in seconds
        """
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx is required for A2AClient. Install with: pip install httpx")
        self.timeout = timeout
        self._agent_cache: Dict[str, RemoteAgent] = {}
        self._client = httpx.Client(timeout=timeout)

    def discover(self, base_url: str, force_refresh: bool = False) -> RemoteAgent:
        """
        Discover a remote agent's capabilities via Agent Card.

        Args:
            base_url: Base URL of the remote agent (e.g., "http://other-agent:7000")
            force_refresh: Force refresh even if cached

        Returns:
            RemoteAgent with discovered capabilities

        Raises:
            URLError: If agent is unreachable
            ValueError: If agent card is invalid
        """
        cache_key = base_url.rstrip("/")

        if not force_refresh and cache_key in self._agent_cache:
            cached = self._agent_cache[cache_key]
            # Refresh if older than 5 minutes
            if cached.discovered_at and (time.time() - cached.discovered_at) < 300:
                return cached

        card_url = f"{cache_key}/.well-known/agent.json"
        logger.info(f"Discovering agent at {card_url}")

        try:
            resp = self._client.get(card_url, headers={"Accept": "application/json"})
            resp.raise_for_status()
            data = resp.json()

            # Parse agent card
            card = AgentCard(
                name=data.get("name", "Unknown"),
                description=data.get("description", ""),
                version=data.get("version", "1.0.0"),
                capabilities=[
                    AgentCapability(**c) for c in data.get("capabilities", [])
                ],
                skills=[
                    AgentSkill(**s) for s in data.get("skills", [])
                ],
                input_modalities=data.get("input_modalities", []),
                output_modalities=data.get("output_modalities", []),
                authentication=data.get("authentication", {}),
                metadata=data.get("metadata", {}),
            )

            agent = RemoteAgent(
                url=cache_key,
                card=card,
                discovered_at=time.time(),
            )
            self._agent_cache[cache_key] = agent
            logger.info(f"Discovered agent: {card.name} with {len(card.capabilities)} capabilities")
            return agent

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error discovering agent: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Network error discovering agent: {e}")
            raise
        except Exception as e:
            logger.exception(f"Error parsing agent card from {card_url}")
            raise ValueError(f"Invalid agent card: {e}")

    def create_task(
        self,
        agent_url: str,
        skill_id: str,
        message: str,
        metadata: Optional[Dict] = None,
        auto_execute: bool = True,
    ) -> Task:
        """
        Create a task on a remote agent.

        Args:
            agent_url: Base URL of the remote agent
            skill_id: ID of the skill/tool to execute
            message: Initial user message
            metadata: Optional metadata
            auto_execute: Whether to start execution immediately

        Returns:
            Task object with ID and initial state
        """
        base_url = agent_url.rstrip("/")
        tasks_url = f"{base_url}/a2a/v1/tasks"

        request_data = {
            "jsonrpc": "2.0",
            "method": "tasks/create",
            "params": {
                "skill_id": skill_id,
                "message": message,
                "metadata": metadata or {},
                "auto_execute": auto_execute,
            },
            "id": 1,
        }

        logger.info(f"Creating task on {base_url} for skill {skill_id}")

        try:
            resp = self._client.post(
                tasks_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = resp.json()

            if "error" in result:
                raise ValueError(f"Task creation failed: {result['error']}")

            task_data = result.get("result", {})
            task = Task(
                id=task_data.get("id"),
                state=TaskState(task_data.get("state", "submitted")),
                skill_id=task_data.get("skill_id"),
                metadata=task_data.get("metadata", {}),
            )
            logger.info(f"Created task {task.id} with state {task.state.value}")
            return task

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating task: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Network error creating task: {e}")
            raise

    def get_task(self, task_id: str, agent_url: str) -> Task:
        """
        Get current state of a task.

        Args:
            task_id: Task ID
            agent_url: Base URL of the remote agent

        Returns:
            Task with current state and artifacts
        """
        base_url = agent_url.rstrip("/")
        task_url = f"{base_url}/a2a/v1/tasks/{task_id}"

        try:
            resp = self._client.get(task_url, headers={"Accept": "application/json"})
            resp.raise_for_status()
            result = resp.json()

            if "error" in result:
                raise ValueError(f"Task not found: {result['error']}")

            task_data = result.get("result", result)
            return self._parse_task(task_data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Task not found: {task_id}")
            raise

    def send_message(
        self,
        task_id: str,
        agent_url: str,
        message: str,
        role: str = "user",
    ) -> Task:
        """
        Send a message to an existing task.

        Args:
            task_id: Task ID
            agent_url: Base URL of the remote agent
            message: Message content
            role: Message role (user, system)

        Returns:
            Updated task
        """
        base_url = agent_url.rstrip("/")
        tasks_url = f"{base_url}/a2a/v1/tasks"

        request_data = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "task_id": task_id,
                "message": message,
                "role": role,
            },
            "id": 1,
        }

        try:
            resp = self._client.post(
                tasks_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = resp.json()

            if "error" in result:
                raise ValueError(f"Send message failed: {result['error']}")

            return self._parse_task(result.get("result", {}))

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending message: {e.response.status_code}")
            raise

    def cancel_task(self, task_id: str, agent_url: str) -> Task:
        """
        Cancel a running task.

        Args:
            task_id: Task ID
            agent_url: Base URL of the remote agent

        Returns:
            Cancelled task
        """
        base_url = agent_url.rstrip("/")
        tasks_url = f"{base_url}/a2a/v1/tasks"

        request_data = {
            "jsonrpc": "2.0",
            "method": "tasks/cancel",
            "params": {"task_id": task_id},
            "id": 1,
        }

        try:
            resp = self._client.post(
                tasks_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = resp.json()

            if "error" in result:
                raise ValueError(f"Cancel failed: {result['error']}")

            return self._parse_task(result.get("result", {}).get("task", {}))

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error cancelling task: {e.response.status_code}")
            raise

    def wait_for_completion(
        self,
        task_id: str,
        agent_url: str,
        poll_interval: float = 1.0,
        timeout: Optional[float] = None,
        on_update: Optional[Callable[[Task], None]] = None,
    ) -> Task:
        """
        Wait for a task to complete by polling.

        Args:
            task_id: Task ID
            agent_url: Base URL of the remote agent
            poll_interval: Seconds between polls
            timeout: Maximum time to wait (None for indefinite)
            on_update: Optional callback for state changes

        Returns:
            Completed task

        Raises:
            TimeoutError: If timeout exceeded
        """
        start_time = time.time()
        last_state = None

        while True:
            task = self.get_task(task_id, agent_url)

            # Notify on state change
            if task.state != last_state:
                last_state = task.state
                if on_update:
                    on_update(task)
                logger.debug(f"Task {task_id} state: {task.state.value}")

            # Check for completion
            if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                return task

            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")

            time.sleep(poll_interval)

    def _parse_task(self, data: Dict) -> Task:
        """Parse task from JSON response."""
        from .types import TaskMessage, TaskArtifact

        task = Task(
            id=data.get("id", ""),
            state=TaskState(data.get("state", "submitted")),
            skill_id=data.get("skill_id"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata", {}),
            error=data.get("error"),
        )

        for msg_data in data.get("messages", []):
            task.messages.append(TaskMessage(
                role=msg_data.get("role", "user"),
                content=msg_data.get("content", ""),
                timestamp=msg_data.get("timestamp", ""),
                parts=msg_data.get("parts", []),
            ))

        for art_data in data.get("artifacts", []):
            task.artifacts.append(TaskArtifact(
                type=art_data.get("type", "text"),
                content=art_data.get("content"),
                name=art_data.get("name"),
                mime_type=art_data.get("mime_type", "text/plain"),
            ))

        return task


# Convenience function for simple task execution
def execute_remote_task(
    agent_url: str,
    skill_id: str,
    message: str,
    timeout: float = 60.0,
) -> Task:
    """
    Execute a task on a remote agent and wait for completion.

    Args:
        agent_url: Base URL of the remote agent
        skill_id: Skill/tool to execute
        message: Task instruction
        timeout: Maximum wait time

    Returns:
        Completed task with artifacts

    Example:
        task = execute_remote_task(
            "http://agent-zero:7000",
            "code_execution",
            "Run pytest tests/ -v"
        )
        print(task.artifacts[0].content)
    """
    client = A2AClient()
    task = client.create_task(agent_url, skill_id, message)
    return client.wait_for_completion(task.id, agent_url, timeout=timeout)
