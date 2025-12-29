"""
PMOVESAgent - Core Agent Class

A production-ready agent implementation that leverages Claude Agent SDK
with full PMOVES ecosystem integration.

Key Features:
- Dynamic model routing via TensorZero (provider::model_name syntax)
- MCP server integration (Hi-RAG, NATS, Supabase)
- Subagent orchestration (researcher, code_reviewer, media_processor, knowledge)
- Hook system for observability (audit, NATS publishing, cost tracking)
- Session persistence with resume/fork/checkpoint

Usage:
    agent = PMOVESAgent(agent_id="research-agent", role="researcher")

    async for message in agent.execute("Analyze the PMOVES architecture"):
        if message.type == "assistant":
            print(message.content)
        elif message.type == "result":
            print(f"Final result: {message.result}")

NATS Events Published:
- agent.tool.pre.v1: Before tool execution
- agent.tool.post.v1: After tool execution
- botz.agent.heartbeat.v1: Agent presence (every 30s)
- botz.work.completed.v1: Task completion
"""

import asyncio
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

# Note: claude_agent_sdk is imported conditionally for type checking
# In production, ensure: pip install claude-agent-sdk
try:
    from claude_agent_sdk import query, ClaudeAgentOptions
    from claude_agent_sdk.tools import tool
    HAS_AGENT_SDK = True
except ImportError:
    HAS_AGENT_SDK = False
    # Stub types for development
    ClaudeAgentOptions = dict

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import nats
    from nats.aio.client import Client as NATSClient
    HAS_NATS = True
except ImportError:
    HAS_NATS = False
    NATSClient = None


class PMOVESAgent:
    """
    PMOVES Agent using Claude Agent SDK with full ecosystem access.

    This agent integrates with:
    - TensorZero Gateway for dynamic model routing
    - Hi-RAG v2 for knowledge retrieval
    - NATS for event-driven coordination
    - Supabase for state persistence
    - Agent Zero for orchestration

    Attributes:
        agent_id: Unique identifier for this agent instance
        role: Functional role (researcher, code_reviewer, media_processor, etc.)
        options: Claude Agent SDK configuration
        nats_client: NATS connection for event publishing
    """

    # Default PMOVES service endpoints
    TENSORZERO_URL = os.getenv("TENSORZERO_URL", "http://localhost:3030")
    HIRAG_URL = os.getenv("HIRAG_URL", "http://localhost:8086")
    NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
    SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:3010")
    AGENT_ZERO_URL = os.getenv("AGENT_ZERO_URL", "http://localhost:8080")

    def __init__(
        self,
        agent_id: str,
        role: str = "general",
        model: str = "openai::qwen3:8b",  # Dynamic TensorZero syntax
        allowed_tools: Optional[list[str]] = None,
        enable_nats: bool = True,
        enable_hooks: bool = True,
    ):
        """
        Initialize a PMOVES Agent.

        Args:
            agent_id: Unique identifier for this agent
            role: Functional role determining available subagents and tools
            model: Model to use (provider::model_name syntax)
            allowed_tools: List of allowed tool names (default: all standard tools)
            enable_nats: Whether to connect to NATS for event publishing
            enable_hooks: Whether to enable observability hooks
        """
        self.agent_id = agent_id
        self.role = role
        self.model = model
        self.enable_nats = enable_nats
        self.enable_hooks = enable_hooks

        self.nats_client: Optional[NATSClient] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Default allowed tools if not specified
        self.allowed_tools = allowed_tools or [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "Task", "WebFetch", "WebSearch", "LSP",
        ]

        # Build Claude Agent SDK options
        self.options = self._build_options()

    def _build_options(self) -> dict:
        """Build ClaudeAgentOptions configuration."""
        options = {
            "allowed_tools": self.allowed_tools,
            "mcp_servers": self._configure_mcp_servers(),
            "agents": self._configure_subagents(),
            "setting_sources": ["project"],  # Load .claude/CLAUDE.md
        }

        if self.enable_hooks:
            options["hooks"] = self._configure_hooks()

        return options

    def _configure_mcp_servers(self) -> dict:
        """
        Configure MCP servers for PMOVES service access.

        Returns dict of MCP server configurations exposing:
        - Hi-RAG for knowledge retrieval
        - TensorZero for model routing
        - NATS for event publishing
        - Supabase for data persistence
        """
        return {
            "hirag": {
                "type": "http",
                "url": self.HIRAG_URL,
                "description": "Hi-RAG v2 hybrid knowledge retrieval",
            },
            "tensorzero": {
                "type": "http",
                "url": f"{self.TENSORZERO_URL}/openai/v1",
                "description": "TensorZero LLM gateway with dynamic model routing",
            },
            "nats": {
                "command": "python",
                "args": ["-m", "pmoves_botz.features.mcp_bridge.tools.nats"],
                "description": "NATS message bus for event coordination",
            },
            "supabase": {
                "type": "http",
                "url": self.SUPABASE_URL,
                "description": "Supabase PostgreSQL with pgvector",
            },
        }

    def _configure_subagents(self) -> dict:
        """
        Configure specialized subagents based on role.

        Subagents are spawned for specific task types:
        - researcher: Deep research via SupaSerch + Hi-RAG
        - code_reviewer: Security-focused code analysis
        - media_processor: Video/audio processing
        - knowledge_manager: Hi-RAG knowledge management
        """
        base_agents = {
            "researcher": {
                "description": "Deep research via SupaSerch + Hi-RAG + DeepResearch",
                "prompt": """You are a research specialist with access to:
- Hi-RAG v2 for semantic search across the knowledge base
- SupaSerch for multimodal holographic research
- DeepResearch for LLM-based research planning
- Web search for current information

Always cite sources and provide confidence levels.""",
                "tools": ["WebSearch", "mcp__hirag__query", "Task"],
            },
            "code_reviewer": {
                "description": "Security-focused code review and analysis",
                "prompt": """You are a security-focused code reviewer. Check for:
- OWASP Top 10 vulnerabilities
- Authentication/authorization issues
- Input validation problems
- SQL injection, XSS, command injection
- Secrets/credentials exposure

Provide severity ratings: Critical, High, Medium, Low.""",
                "tools": ["Read", "Grep", "Glob", "LSP"],
            },
            "media_processor": {
                "description": "Video/audio analysis and processing",
                "prompt": """You are a media processing specialist with access to:
- PMOVES.YT for YouTube ingestion
- FFmpeg-Whisper for transcription
- Media analyzers for object/emotion detection
- MinIO for artifact storage

Coordinate media workflows efficiently.""",
                "tools": ["Bash", "Read", "mcp__tensorzero__embeddings"],
            },
            "knowledge_manager": {
                "description": "Hi-RAG knowledge base management",
                "prompt": """You manage the PMOVES knowledge base using:
- Qdrant for vector embeddings
- Neo4j for knowledge graph
- Meilisearch for full-text search
- Extract Worker for ingestion

Optimize retrieval and maintain index health.""",
                "tools": ["mcp__hirag__query", "mcp__supabase__query", "Bash"],
            },
        }

        # Role-specific agent selection
        if self.role == "researcher":
            return {"researcher": base_agents["researcher"]}
        elif self.role == "code_reviewer":
            return {"code_reviewer": base_agents["code_reviewer"]}
        elif self.role == "media_processor":
            return {"media_processor": base_agents["media_processor"]}
        elif self.role == "knowledge_manager":
            return {"knowledge_manager": base_agents["knowledge_manager"]}
        else:
            # General role gets all subagents
            return base_agents

    def _configure_hooks(self) -> dict:
        """
        Configure observability hooks.

        Hooks fire at key points:
        - PreToolUse: Audit and validate tool calls
        - PostToolUse: Publish events, track costs
        """
        return {
            "PreToolUse": [
                {
                    "matcher": {"tool_name": "*"},  # Match all tools
                    "hooks": [
                        {
                            "type": "command",
                            "command": self._get_pre_tool_hook_command(),
                        }
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": {"tool_name": "*"},
                    "hooks": [
                        {
                            "type": "command",
                            "command": self._get_post_tool_hook_command(),
                        }
                    ],
                }
            ],
        }

    def _get_pre_tool_hook_command(self) -> str:
        """Get the pre-tool hook command for audit logging."""
        # In production, this would call the hooks/audit.py script
        return f"python -m pmoves_botz.features.agent_sdk.hooks.audit --agent-id {self.agent_id} --phase pre"

    def _get_post_tool_hook_command(self) -> str:
        """Get the post-tool hook command for event publishing."""
        return f"python -m pmoves_botz.features.agent_sdk.hooks.nats_publisher --agent-id {self.agent_id}"

    async def connect(self, require_services: bool = True) -> None:
        """
        Connect to PMOVES services (NATS, HTTP clients).

        Call this before execute() for full functionality.

        Args:
            require_services: If True (default), NATS connection failures raise ConnectionError.
                             If False, NATS failures are logged but execution continues.

        Raises:
            ConnectionError: If NATS connection fails and enable_nats=True and require_services=True.
            RuntimeError: If required dependencies are not installed.

        """
        if HAS_HTTPX:
            self._http_client = httpx.AsyncClient(timeout=30.0)

        if self.enable_nats:
            if not HAS_NATS:
                raise RuntimeError(
                    "NATS dependencies not installed. "
                    "Run: pip install nats-py"
                )
            try:
                self.nats_client = await nats.connect(
                    self.NATS_URL,
                    connect_timeout=10,
                    reconnect=False,
                )
                # Start heartbeat
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            except (ConnectionRefusedError, OSError) as e:
                if require_services:
                    raise ConnectionError(
                        f"Cannot connect to NATS at {self.NATS_URL}. "
                        f"Ensure NATS is running: docker compose up -d nats"
                    ) from e
                # If services not required, log warning and continue
                print(f"Warning: Could not connect to NATS: {e}")
                self.nats_client = None

    async def disconnect(self) -> None:
        """Disconnect from PMOVES services."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.nats_client:
            await self.nats_client.close()

        if self._http_client:
            await self._http_client.aclose()

    async def _heartbeat_loop(self) -> None:
        """Publish agent heartbeat to NATS every 30 seconds."""
        while True:
            try:
                await self._publish_event("botz.agent.heartbeat.v1", {
                    "agent_id": self.agent_id,
                    "agent_type": "sdk",
                    "role": self.role,
                    "model": self.model,
                    "status": "active",
                    "capabilities": self.allowed_tools,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Heartbeat error: {e}")
                await asyncio.sleep(30)

    async def _publish_event(self, subject: str, payload: dict) -> None:
        """Publish an event to NATS."""
        if self.nats_client:
            import json
            await self.nats_client.publish(
                subject,
                json.dumps(payload).encode()
            )

    async def execute(
        self,
        task: str,
        session_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> AsyncGenerator[Any, None]:
        """Execute a task with full PMOVES integration.

        This method streams messages from the Claude Agent SDK while publishing
        events to NATS for observability. Messages include assistant responses,
        tool use, and final results.

        Args:
            task: The task description or prompt to execute.
            session_id: Optional session ID for resuming previous sessions.
            context: Optional additional context dict for task execution.

        Yields:
            Message objects from Claude Agent SDK with types:
                - "assistant": Text responses from the model
                - "tool_use": Tool invocations
                - "result": Final task completion result

        Raises:
            RuntimeError: If Claude Agent SDK is not installed.
            ConnectionError: If NATS connection fails during event publishing.
            Exception: For errors during task execution (published to NATS).

        Example:
            >>> async for message in agent.execute("Analyze PMOVES architecture"):
            ...     if message.type == "assistant":
            ...         print(message.content)
            ...     elif message.type == "result":
            ...         print(f"Result: {message.result}")
        """
        if not HAS_AGENT_SDK:
            raise RuntimeError(
                "Claude Agent SDK not installed. "
                "Install with: pip install claude-agent-sdk"
            )

        # Build the full prompt with context
        full_prompt = self._build_prompt(task, context)

        # Configure options with optional session resume
        options = ClaudeAgentOptions(**self.options)
        if session_id:
            options.resume = session_id

        # Publish task start event
        await self._publish_event("agent.task.start.v1", {
            "agent_id": self.agent_id,
            "task": task[:200],  # Truncate for event
            "model": self.model,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

        try:
            async for message in query(prompt=full_prompt, options=options):
                yield message

                # Track result
                if hasattr(message, 'type') and message.type == "result":
                    await self._publish_event("botz.work.completed.v1", {
                        "agent_id": self.agent_id,
                        "task": task[:200],
                        "status": "success",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    })
        except Exception as e:
            await self._publish_event("botz.work.completed.v1", {
                "agent_id": self.agent_id,
                "task": task[:200],
                "status": "failure",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
            raise

    def _build_prompt(self, task: str, context: Optional[dict] = None) -> str:
        """Build the full prompt with role context."""
        role_contexts = {
            "researcher": "You are a PMOVES research agent with access to Hi-RAG, SupaSerch, and DeepResearch.",
            "code_reviewer": "You are a PMOVES code review agent focused on security and quality.",
            "media_processor": "You are a PMOVES media processing agent for video/audio workflows.",
            "knowledge_manager": "You are a PMOVES knowledge management agent for Hi-RAG operations.",
            "general": "You are a PMOVES general-purpose agent with full ecosystem access.",
        }

        prompt_parts = [
            role_contexts.get(self.role, role_contexts["general"]),
            "",
            "## Task",
            task,
        ]

        if context:
            prompt_parts.extend([
                "",
                "## Additional Context",
                str(context),
            ])

        return "\n".join(prompt_parts)

    async def delegate_to_local(
        self,
        task: str,
        model: str = "openai::qwen3:8b",
        timeout: float = 300.0,
    ) -> dict:
        """Delegate a task to a local model via TensorZero.

        This method is useful for routine tasks that don't need cloud models,
        saving API costs while maintaining quality. Publishes handoff events
        to NATS for observability.

        Args:
            task: Task description or prompt to execute.
            model: Local model identifier in "provider::model_name" format (default: "openai::qwen3:8b").
            timeout: Request timeout in seconds (default: 300.0).

        Returns:
            Response dict from TensorZero with keys:
                - "choices": Array of model responses
                - "usage": Token usage statistics
                - "model": Model identifier used

        Raises:
            RuntimeError: If HTTP client is not initialized (call connect() first).
            httpx.HTTPStatusError: If TensorZero returns an error status.
            httpx.TimeoutException: If request exceeds timeout duration.
            ConnectionError: If TensorZero service is unavailable.

        Example:
            >>> await agent.connect()
            >>> result = await agent.delegate_to_local("Summarize PMOVES architecture")
            >>> print(result['choices'][0]['message']['content'])
        """
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized. Call connect() first.")

        # Publish handoff event
        await self._publish_event("agent.handoff.request.v1", {
            "from_agent": self.agent_id,
            "to": "local",
            "model": model,
            "task": task[:200],
            "reason": "local_model_suitable",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

        response = await self._http_client.post(
            f"{self.TENSORZERO_URL}/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are a {self.role} agent."},
                    {"role": "user", "content": task},
                ],
            },
            timeout=timeout,
        )
        response.raise_for_status()

        result = response.json()

        await self._publish_event("agent.handoff.completed.v1", {
            "from_agent": self.agent_id,
            "model": model,
            "status": "success",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

        return result

    async def query_hirag(
        self,
        query: str,
        top_k: int = 10,
        rerank: bool = True,
    ) -> dict:
        """Query Hi-RAG v2 knowledge base directly.

        This method performs hybrid retrieval combining vector search (Qdrant),
        graph traversal (Neo4j), and full-text search (Meilisearch) with optional
        cross-encoder reranking for improved relevance.

        Args:
            query: Natural language search query.
            top_k: Number of results to return (default: 10).
            rerank: Whether to apply cross-encoder reranking for better relevance (default: True).

        Returns:
            Hi-RAG response dict with keys:
                - "results": List of search results with metadata
                - "query": The original query
                - "total": Total number of results found

        Raises:
            RuntimeError: If HTTP client is not initialized (call connect() first).
            httpx.HTTPStatusError: If Hi-RAG service returns an error status.
            ConnectionError: If Hi-RAG service is unavailable.

        Example:
            >>> await agent.connect()
            >>> result = await agent.query_hirag("How does TensorZero routing work?")
            >>> print(f"Found {len(result['results']} results")
        """
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized. Call connect() first.")

        response = await self._http_client.post(
            f"{self.HIRAG_URL}/hirag/query",
            json={
                "query": query,
                "top_k": top_k,
                "rerank": rerank,
            },
        )
        response.raise_for_status()
        return response.json()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False


# Convenience function for quick agent creation
async def create_agent(
    agent_id: str,
    role: str = "general",
    **kwargs
) -> PMOVESAgent:
    """
    Create and connect a PMOVES agent.

    Args:
        agent_id: Unique agent identifier
        role: Agent role (researcher, code_reviewer, etc.)
        **kwargs: Additional PMOVESAgent arguments

    Returns:
        Connected PMOVESAgent instance
    """
    agent = PMOVESAgent(agent_id=agent_id, role=role, **kwargs)
    await agent.connect()
    return agent
