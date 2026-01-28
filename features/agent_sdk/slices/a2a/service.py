"""
A2A Slice - Service Layer.

Wraps the gateway's A2A client for use by SDK agents.
Provides high-level methods for agent-to-agent communication.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import from gateway A2A module
try:
    from a2a import A2AClient, RemoteAgent, Task, TaskState, execute_remote_task
    A2A_AVAILABLE = True
except ImportError:
    A2A_AVAILABLE = False
    A2AClient = None
    RemoteAgent = None
    Task = None
    TaskState = None


class A2AService:
    """
    A2A Service - Agent-to-Agent protocol wrapper for SDK agents.

    This service provides high-level methods for:
    - Discovering remote agents
    - Delegating tasks to remote agents
    - Managing task lifecycle

    Usage:
        service = A2AService()

        # Discover agent capabilities
        agent = await service.discover("http://other-agent:7000")
        print(agent.card.capabilities)

        # Delegate a task
        result = await service.delegate(
            agent_url="http://other-agent:7000",
            skill_id="code_execution",
            message="Run pytest tests/",
        )
        print(result.artifacts)
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize A2A Service.

        Args:
            timeout: Default timeout for A2A operations in seconds
        """
        if not A2A_AVAILABLE:
            logger.warning("A2A module not available - install from gateway")
            self._client = None
        else:
            self._client = A2AClient(timeout=timeout)

        self._agent_registry: Dict[str, RemoteAgent] = {}

    @property
    def available(self) -> bool:
        """Check if A2A is available."""
        return A2A_AVAILABLE and self._client is not None

    def discover(self, agent_url: str, force_refresh: bool = False) -> Optional[RemoteAgent]:
        """
        Discover a remote agent's capabilities.

        Args:
            agent_url: Base URL of the remote agent
            force_refresh: Force refresh even if cached

        Returns:
            RemoteAgent with discovered capabilities, or None if unavailable
        """
        if not self.available:
            logger.error("A2A not available")
            return None

        try:
            agent = self._client.discover(agent_url, force_refresh=force_refresh)
            self._agent_registry[agent_url] = agent
            logger.info(f"Discovered agent: {agent.name} with {len(agent.capabilities)} capabilities")
            return agent
        except Exception as e:
            logger.error(f"Failed to discover agent at {agent_url}: {e}")
            return None

    def delegate(
        self,
        agent_url: str,
        skill_id: str,
        message: str,
        timeout: float = 60.0,
        metadata: Optional[Dict] = None,
    ) -> Optional[Task]:
        """
        Delegate a task to a remote agent.

        Args:
            agent_url: Base URL of the remote agent
            skill_id: Skill/tool to execute
            message: Task instruction
            timeout: Maximum wait time
            metadata: Optional task metadata

        Returns:
            Completed Task with artifacts, or None if failed
        """
        if not self.available:
            logger.error("A2A not available")
            return None

        try:
            # Create task
            task = self._client.create_task(
                agent_url=agent_url,
                skill_id=skill_id,
                message=message,
                metadata=metadata,
            )
            logger.info(f"Created task {task.id} on {agent_url}")

            # Wait for completion
            task = self._client.wait_for_completion(
                task_id=task.id,
                agent_url=agent_url,
                timeout=timeout,
            )

            if task.state == TaskState.COMPLETED:
                logger.info(f"Task {task.id} completed successfully")
            else:
                logger.warning(f"Task {task.id} ended with state: {task.state.value}")

            return task

        except Exception as e:
            logger.error(f"Failed to delegate task to {agent_url}: {e}")
            return None

    def list_registered_agents(self) -> List[RemoteAgent]:
        """List all discovered agents."""
        return list(self._agent_registry.values())

    def get_agent(self, agent_url: str) -> Optional[RemoteAgent]:
        """Get a cached agent by URL."""
        return self._agent_registry.get(agent_url)

    async def broadcast(
        self,
        skill_id: str,
        message: str,
        agent_urls: Optional[List[str]] = None,
    ) -> Dict[str, Task]:
        """
        Broadcast a task to multiple agents.

        Args:
            skill_id: Skill to execute
            message: Task instruction
            agent_urls: List of agent URLs (default: all registered)

        Returns:
            Dict mapping agent URL to Task result
        """
        urls = agent_urls or list(self._agent_registry.keys())
        results = {}

        for url in urls:
            result = self.delegate(url, skill_id, message)
            results[url] = result

        return results
