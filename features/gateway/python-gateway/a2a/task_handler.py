"""
A2A Task Handler - JSON-RPC 2.0 Task Lifecycle Management.

Implements the A2A task lifecycle:
- tasks/create: Create a new task
- tasks/get: Get task status and artifacts
- tasks/list: List all tasks
- tasks/cancel: Cancel a running task
- tasks/send: Send a message to a task

Reference: docs/agents/AI Agent Integration and Best Practices.md (Section 3.2.2)
"""

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import uuid

from .types import Task, TaskState, TaskMessage, TaskArtifact

logger = logging.getLogger(__name__)


class TaskStore:
    """
    In-memory task storage with thread-safe operations.

    For production, replace with Redis or database backend.
    """

    def __init__(self, max_tasks: int = 1000):
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._max_tasks = max_tasks

    def create(self, skill_id: Optional[str] = None, metadata: Optional[Dict] = None) -> Task:
        """Create a new task."""
        with self._lock:
            # Evict old completed tasks if at capacity
            if len(self._tasks) >= self._max_tasks:
                evicted = self._evict_old_tasks()
                # If no tasks were evicted and still at capacity, raise error
                if evicted == 0 and len(self._tasks) >= self._max_tasks:
                    raise ValueError(
                        f"Task store at capacity ({self._max_tasks}). "
                        "No completed tasks available for eviction."
                    )

            task = Task(
                skill_id=skill_id,
                metadata=metadata or {},
            )
            self._tasks[task.id] = task
            logger.info(f"Created task {task.id} for skill {skill_id}")
            return task

    def get(self, task_id: str) -> Optional[Task]:
        """Get a task by ID (thread-safe)."""
        with self._lock:
            return self._tasks.get(task_id)

    def list_all(self, state: Optional[TaskState] = None, limit: int = 100) -> List[Task]:
        """List tasks, optionally filtered by state (thread-safe)."""
        with self._lock:
            tasks = list(self._tasks.values())
        if state:
            tasks = [t for t in tasks if t.state == state]
        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def update(self, task: Task) -> None:
        """Update a task in the store."""
        with self._lock:
            if task.id in self._tasks:
                self._tasks[task.id] = task

    def delete(self, task_id: str) -> bool:
        """Delete a task."""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    def _evict_old_tasks(self) -> int:
        """Evict oldest completed/failed tasks to make room.

        Returns:
            Number of tasks evicted.
        """
        completed = [
            t for t in self._tasks.values()
            if t.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
        ]
        completed.sort(key=lambda t: t.updated_at)

        if not completed:
            return 0

        # Remove oldest 20% of completed tasks (at least 1)
        to_remove = completed[:max(1, len(completed) // 5)]
        for task in to_remove:
            del self._tasks[task.id]
            logger.debug(f"Evicted task {task.id}")

        return len(to_remove)


class TaskHandler:
    """
    A2A Task Handler - Manages task lifecycle and execution.

    Integrates with MCP Gateway for tool execution.
    """

    def __init__(
        self,
        tool_executor: Callable[[str, Dict], Dict],
        max_workers: int = 4,
    ):
        """
        Initialize TaskHandler.

        Args:
            tool_executor: Callable that executes MCP tools (qualified_name, arguments) -> result
            max_workers: Max concurrent task workers
        """
        self.store = TaskStore()
        self.tool_executor = tool_executor
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_tasks: Dict[str, threading.Event] = {}

    def handle_jsonrpc(self, request: Dict) -> Dict:
        """
        Handle JSON-RPC 2.0 request.

        Supported methods:
        - tasks/create
        - tasks/get
        - tasks/list
        - tasks/cancel
        - tasks/send
        """
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id", 1)

        try:
            if method == "tasks/create":
                result = self._create_task(params)
            elif method == "tasks/get":
                result = self._get_task(params)
            elif method == "tasks/list":
                result = self._list_tasks(params)
            elif method == "tasks/cancel":
                result = self._cancel_task(params)
            elif method == "tasks/send":
                result = self._send_message(params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }

        except Exception as e:
            logger.exception(f"Error handling {method}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(e)}
            }

    def _create_task(self, params: Dict) -> Dict:
        """
        Create a new task.

        Params:
            skill_id: Optional skill/tool to execute
            message: Initial user message
            metadata: Optional metadata
            auto_execute: Whether to start execution immediately (default: True)
        """
        skill_id = params.get("skill_id")
        message = params.get("message", "")
        metadata = params.get("metadata", {})
        auto_execute = params.get("auto_execute", True)

        task = self.store.create(skill_id=skill_id, metadata=metadata)

        if message:
            task.add_message("user", message)

        if auto_execute and skill_id:
            self._start_task_execution(task)

        return task.to_dict()

    def _get_task(self, params: Dict) -> Dict:
        """Get task by ID."""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("task_id is required")

        task = self.store.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        return task.to_dict()

    def _list_tasks(self, params: Dict) -> Dict:
        """List tasks with optional filtering."""
        state_str = params.get("state")
        state = TaskState(state_str) if state_str else None
        limit = params.get("limit", 100)

        tasks = self.store.list_all(state=state, limit=limit)
        return {
            "tasks": [t.to_dict() for t in tasks],
            "count": len(tasks),
        }

    def _cancel_task(self, params: Dict) -> Dict:
        """Cancel a running task."""
        task_id = params.get("task_id")
        if not task_id:
            raise ValueError("task_id is required")

        task = self.store.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Check if task is already in a terminal state
        terminal_states = (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
        if task.state in terminal_states:
            return {
                "cancelled": False,
                "reason": f"Task already in terminal state: {task.state.value}",
                "task": task.to_dict(),
            }

        # Signal cancellation
        if task_id in self._running_tasks:
            self._running_tasks[task_id].set()

        task.update_state(TaskState.CANCELLED)
        self.store.update(task)

        return {"cancelled": True, "task": task.to_dict()}

    def _send_message(self, params: Dict) -> Dict:
        """Send a message to an existing task."""
        task_id = params.get("task_id")
        message = params.get("message", "")
        role = params.get("role", "user")

        if not task_id:
            raise ValueError("task_id is required")

        task = self.store.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        task.add_message(role, message)
        self.store.update(task)

        # If task was waiting for input, resume execution
        if task.state == TaskState.INPUT_REQUIRED:
            self._start_task_execution(task)

        return task.to_dict()

    def _start_task_execution(self, task: Task) -> None:
        """Start async task execution."""
        cancel_event = threading.Event()
        self._running_tasks[task.id] = cancel_event

        def execute():
            try:
                self._execute_task(task, cancel_event)
            finally:
                self._running_tasks.pop(task.id, None)

        self.executor.submit(execute)

    def _execute_task(self, task: Task, cancel_event: threading.Event) -> None:
        """
        Execute a task by calling the appropriate tool.

        This is the main execution logic that bridges A2A tasks to MCP tools.
        """
        try:
            task.update_state(TaskState.WORKING)
            self.store.update(task)
            task.add_message("system", "Task execution started")

            # Check for cancellation
            if cancel_event.is_set():
                task.update_state(TaskState.CANCELLED)
                self.store.update(task)
                return

            # Get the last user message as the task input
            user_messages = [m for m in task.messages if m.role == "user"]
            if not user_messages:
                task.fail("No user message provided")
                self.store.update(task)
                return

            last_message = user_messages[-1].content

            # Determine which tool to call
            tool_name = task.skill_id
            if not tool_name:
                # Try to extract from metadata or default to a general handler
                tool_name = task.metadata.get("tool")

            if not tool_name:
                task.fail("No skill_id or tool specified")
                self.store.update(task)
                return

            # Build arguments from the message
            arguments = task.metadata.get("arguments", {})
            if "input" not in arguments:
                arguments["input"] = last_message

            # Execute via MCP Gateway
            logger.info(f"Task {task.id}: Executing {tool_name} with {arguments}")
            result = self.tool_executor(tool_name, arguments)

            # Check for cancellation again
            if cancel_event.is_set():
                task.update_state(TaskState.CANCELLED)
                self.store.update(task)
                return

            # Process result
            if "error" in result:
                task.fail(result["error"])
            else:
                # Extract result content
                content = result.get("result", result)
                if isinstance(content, dict) and "content" in content:
                    # MCP tool result format
                    content = content["content"]
                    if isinstance(content, list) and len(content) > 0:
                        content = content[0].get("text", str(content))

                task.add_artifact("result", content, name=f"{tool_name}_output")
                task.add_message("agent", f"Completed: {str(content)[:200]}...")
                task.complete()

            self.store.update(task)
            logger.info(f"Task {task.id}: Completed with state {task.state.value}")

        except Exception as e:
            logger.exception(f"Task {task.id} execution error")
            task.fail(str(e))
            self.store.update(task)

    def shutdown(self) -> None:
        """Shutdown the executor and cancel running tasks."""
        # Signal all running tasks to cancel
        for event in self._running_tasks.values():
            event.set()

        self.executor.shutdown(wait=True)
