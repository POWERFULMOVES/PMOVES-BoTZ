"""
PMOVES Agent SDK Integration

Provides a unified multi-agent framework leveraging Claude Agent SDK
with full PMOVES ecosystem integration.

Key Components:
- PMOVESAgent: Core agent class with MCP, NATS, and TensorZero integration
- SessionManager: Persistent sessions with resume/fork/checkpoint
- Subagents: Specialized agents for research, code review, media, knowledge
- Hooks: Audit, NATS publishing, cost tracking

Usage:
    from pmoves_botz.features.agent_sdk import PMOVESAgent, SessionManager

    agent = PMOVESAgent(agent_id="my-agent", role="researcher")
    async for msg in agent.execute("Research quantum computing"):
        print(msg)

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                    PMOVES Multi-Agent Hub                        │
    ├─────────────────────────────────────────────────────────────────┤
    │  CLIs                    │  Agent SDK Services                   │
    │  ├─ Claude Code          │  ├─ Agent Zero (Orchestrator)        │
    │  ├─ PMOVES-Crush         │  ├─ Research Agent (SupaSerch)       │
    │  └─ Custom CLIs          │  ├─ Media Agent (Video/Audio)        │
    │                          │  └─ Knowledge Agent (Hi-RAG)         │
    ├─────────────────────────────────────────────────────────────────┤
    │                    MCP Bridge Layer                              │
    │  ├─ pmoves-mcp (PMOVES services as MCP tools)                   │
    │  ├─ tensorzero-mcp (Model routing)                              │
    │  ├─ nats-mcp (Event bus)                                        │
    │  └─ hirag-mcp (Knowledge retrieval)                             │
    ├─────────────────────────────────────────────────────────────────┤
    │                    NATS Event Bus                                │
    │  botz.agent.*, crush.*, claude.code.*, agent.handoff.*          │
    └─────────────────────────────────────────────────────────────────┘
"""

from .pmoves_agent import PMOVESAgent
from .session_manager import PMOVESSessionManager

__all__ = [
    "PMOVESAgent",
    "PMOVESSessionManager",
]

__version__ = "0.1.0"
