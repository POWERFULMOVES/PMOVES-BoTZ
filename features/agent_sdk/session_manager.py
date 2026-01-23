"""
PMOVES Session Manager

Manages agent sessions with persistence and advanced features:
- Resume: Continue from previous session state
- Fork: Branch session for parallel exploration
- Checkpoint: Save state for potential rollback

Storage backends:
- Supabase (default): PostgreSQL with session table
- SurrealDB: Open Notebook integration
- File: Local JSON for development

Usage:
    manager = PMOVESSessionManager()
    await manager.connect()

    # Resume previous session
    async for msg in manager.resume(session_id, "Continue analysis"):
        print(msg)

    # Fork session for exploration
    async for msg in manager.fork(session_id, "Try alternative approach"):
        print(msg)

    # Save checkpoint
    await manager.checkpoint(session_id)
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from dataclasses import dataclass, asdict

try:
    from claude_agent_sdk import query, ClaudeAgentOptions
    HAS_AGENT_SDK = True
except ImportError:
    HAS_AGENT_SDK = False
    ClaudeAgentOptions = dict

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@dataclass
class SessionState:
    """Represents a session's persistent state."""
    session_id: str
    agent_id: str
    role: str
    created_at: str
    updated_at: str
    parent_session_id: Optional[str] = None
    fork_count: int = 0
    checkpoint_count: int = 0
    status: str = "active"  # active, completed, archived
    context: Optional[dict] = None
    metadata: Optional[dict] = None


class PMOVESSessionManager:
    """
    Manage agent sessions with persistence and forking.

    Supports multiple storage backends:
    - Supabase: Production PostgreSQL storage
    - SurrealDB: Open Notebook integration
    - File: Local development storage

    Attributes:
        storage_backend: Storage type ("supabase", "surrealdb", "file")
        sessions_dir: Directory for file-based storage
    """

    SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:3010")
    SURREALDB_URL = os.getenv("OPEN_NOTEBOOK_API_URL", "")

    def __init__(
        self,
        storage_backend: str = "file",
        sessions_dir: Optional[str] = None,
    ):
        """
        Initialize session manager.

        Args:
            storage_backend: Storage type ("supabase", "surrealdb", "file")
            sessions_dir: Directory for file storage (default: ~/.pmoves/sessions)
        """
        self.storage_backend = storage_backend
        self.sessions_dir = Path(
            sessions_dir or os.path.expanduser("~/.pmoves/sessions")
        )
        self._http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Connect to storage backend."""
        if self.storage_backend == "file":
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
        elif HAS_HTTPX:
            self._http_client = httpx.AsyncClient(timeout=30.0)

    async def disconnect(self) -> None:
        """Disconnect from storage backend."""
        if self._http_client:
            await self._http_client.aclose()

    async def create_session(
        self,
        agent_id: str,
        role: str = "general",
        context: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> SessionState:
        """
        Create a new session.

        Args:
            agent_id: Agent identifier
            role: Agent role
            context: Initial context dict
            metadata: Additional metadata

        Returns:
            New SessionState instance
        """
        import uuid
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        state = SessionState(
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            created_at=now,
            updated_at=now,
            context=context,
            metadata=metadata,
        )

        await self._save_state(state)
        return state

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionState if found, None otherwise
        """
        return await self._load_state(session_id)

    async def update_session(
        self,
        session_id: str,
        context: Optional[dict] = None,
        metadata: Optional[dict] = None,
        status: Optional[str] = None,
    ) -> SessionState:
        """
        Update an existing session.

        Args:
            session_id: Session to update
            context: New context (merged with existing)
            metadata: New metadata (merged with existing)
            status: New status

        Returns:
            Updated SessionState
        """
        state = await self._load_state(session_id)
        if not state:
            raise ValueError(f"Session not found: {session_id}")

        state.updated_at = datetime.utcnow().isoformat() + "Z"

        if context:
            if state.context:
                state.context.update(context)
            else:
                state.context = context

        if metadata:
            if state.metadata:
                state.metadata.update(metadata)
            else:
                state.metadata = metadata

        if status:
            state.status = status

        await self._save_state(state)
        return state

    async def resume(
        self,
        session_id: str,
        task: str,
        options: Optional[dict] = None,
    ) -> AsyncGenerator[Any, None]:
        """
        Resume previous session with full context.

        Args:
            session_id: Session to resume
            task: New task to execute
            options: Additional Claude Agent SDK options

        Yields:
            Message objects from continued execution
        """
        if not HAS_AGENT_SDK:
            raise RuntimeError("Claude Agent SDK not installed")

        state = await self.get_session(session_id)
        if not state:
            raise ValueError(f"Session not found: {session_id}")

        # Build options with resume
        agent_options = ClaudeAgentOptions(
            resume=session_id,
            **(options or {})
        )

        # Update session
        await self.update_session(session_id, metadata={"last_task": task})

        async for msg in query(prompt=task, options=agent_options):
            yield msg

    async def fork(
        self,
        session_id: str,
        task: str,
        options: Optional[dict] = None,
    ) -> AsyncGenerator[Any, None]:
        """
        Fork session for parallel exploration.

        Creates a new session branched from the original,
        preserving the original for potential return.

        Args:
            session_id: Session to fork from
            task: Task for forked session
            options: Additional options

        Yields:
            Message objects from forked execution
        """
        if not HAS_AGENT_SDK:
            raise RuntimeError("Claude Agent SDK not installed")

        state = await self.get_session(session_id)
        if not state:
            raise ValueError(f"Session not found: {session_id}")

        # Create forked session
        import uuid
        fork_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        fork_state = SessionState(
            session_id=fork_id,
            agent_id=state.agent_id,
            role=state.role,
            created_at=now,
            updated_at=now,
            parent_session_id=session_id,
            context=state.context.copy() if state.context else None,
            metadata={
                "forked_from": session_id,
                "fork_task": task,
            },
        )

        await self._save_state(fork_state)

        # Update parent fork count
        state.fork_count += 1
        state.updated_at = now
        await self._save_state(state)

        # Execute with fork
        agent_options = ClaudeAgentOptions(
            resume=session_id,
            fork_session=True,
            **(options or {})
        )

        async for msg in query(prompt=task, options=agent_options):
            yield msg

    async def checkpoint(
        self,
        session_id: str,
        label: Optional[str] = None,
    ) -> str:
        """
        Save checkpoint for potential rollback.

        Args:
            session_id: Session to checkpoint
            label: Optional human-readable label

        Returns:
            Checkpoint ID
        """
        state = await self.get_session(session_id)
        if not state:
            raise ValueError(f"Session not found: {session_id}")

        import uuid
        checkpoint_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "created_at": now,
            "label": label or f"checkpoint-{state.checkpoint_count + 1}",
            "state_snapshot": asdict(state),
        }

        # Save checkpoint
        if self.storage_backend == "file":
            checkpoint_file = self.sessions_dir / f"checkpoint_{checkpoint_id}.json"
            checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))
        elif self.storage_backend == "supabase" and self._http_client:
            await self._http_client.post(
                f"{self.SUPABASE_URL}/rest/v1/session_checkpoints",
                json=checkpoint_data,
            )

        # Update checkpoint count
        state.checkpoint_count += 1
        state.updated_at = now
        if state.metadata:
            state.metadata["last_checkpoint"] = checkpoint_id
        else:
            state.metadata = {"last_checkpoint": checkpoint_id}
        await self._save_state(state)

        return checkpoint_id

    async def list_sessions(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[SessionState]:
        """
        List sessions with optional filtering.

        Args:
            agent_id: Filter by agent
            status: Filter by status
            limit: Maximum results

        Returns:
            List of matching sessions
        """
        sessions = []

        if self.storage_backend == "file":
            for session_file in self.sessions_dir.glob("session_*.json"):
                try:
                    data = json.loads(session_file.read_text())
                    state = SessionState(**data)

                    if agent_id and state.agent_id != agent_id:
                        continue
                    if status and state.status != status:
                        continue

                    sessions.append(state)

                    if len(sessions) >= limit:
                        break
                except Exception:
                    continue

        elif self.storage_backend == "supabase" and self._http_client:
            params = {"limit": limit}
            if agent_id:
                params["agent_id"] = f"eq.{agent_id}"
            if status:
                params["status"] = f"eq.{status}"

            response = await self._http_client.get(
                f"{self.SUPABASE_URL}/rest/v1/agent_sessions",
                params=params,
            )
            if response.status_code == 200:
                for data in response.json():
                    sessions.append(SessionState(**data))

        return sessions

    async def archive_session(self, session_id: str) -> None:
        """
        Archive a session (mark as inactive).

        Args:
            session_id: Session to archive
        """
        await self.update_session(session_id, status="archived")

    async def _save_state(self, state: SessionState) -> None:
        """Save session state to storage backend."""
        data = asdict(state)

        if self.storage_backend == "file":
            session_file = self.sessions_dir / f"session_{state.session_id}.json"
            session_file.write_text(json.dumps(data, indent=2))

        elif self.storage_backend == "supabase" and self._http_client:
            await self._http_client.post(
                f"{self.SUPABASE_URL}/rest/v1/agent_sessions",
                json=data,
                headers={"Prefer": "resolution=merge-duplicates"},
            )

        elif self.storage_backend == "surrealdb" and self._http_client:
            await self._http_client.post(
                f"{self.SURREALDB_URL}/sessions",
                json=data,
            )

    async def _load_state(self, session_id: str) -> Optional[SessionState]:
        """Load session state from storage backend."""
        if self.storage_backend == "file":
            session_file = self.sessions_dir / f"session_{session_id}.json"
            if session_file.exists():
                data = json.loads(session_file.read_text())
                return SessionState(**data)

        elif self.storage_backend == "supabase" and self._http_client:
            response = await self._http_client.get(
                f"{self.SUPABASE_URL}/rest/v1/agent_sessions",
                params={"session_id": f"eq.{session_id}"},
            )
            if response.status_code == 200:
                results = response.json()
                if results:
                    return SessionState(**results[0])

        elif self.storage_backend == "surrealdb" and self._http_client:
            response = await self._http_client.get(
                f"{self.SURREALDB_URL}/sessions/{session_id}",
            )
            if response.status_code == 200:
                return SessionState(**response.json())

        return None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False
