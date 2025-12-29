"""
PMOVES MCP Bridge Layer

Exposes PMOVES services as MCP (Model Context Protocol) tools,
enabling any MCP-compatible agent to access the PMOVES ecosystem.

Available Tool Categories:
- Hi-RAG: Knowledge retrieval (query, similarity search, graph)
- NATS: Event publishing and subscription
- TensorZero: LLM routing with dynamic model selection
- Supabase: Database operations

Usage:
    # Start the combined MCP server
    python -m pmoves_botz.features.mcp_bridge.server

    # Or use individual tool modules
    from pmoves_botz.features.mcp_bridge.tools import hirag, nats, tensorzero

Architecture:
    ┌──────────────────────────────────────────────────────┐
    │                MCP Bridge Server                      │
    ├──────────────────────────────────────────────────────┤
    │  Tools                                                │
    │  ├─ hirag_query        (POST /hirag/query)           │
    │  ├─ hirag_similarity   (POST /hirag/similarity)      │
    │  ├─ nats_publish       (NATS pub)                    │
    │  ├─ nats_subscribe     (NATS sub)                    │
    │  ├─ tensorzero_chat    (POST /v1/chat/completions)   │
    │  ├─ tensorzero_embed   (POST /v1/embeddings)         │
    │  ├─ supabase_query     (PostgreSQL)                  │
    │  └─ supabase_insert    (PostgreSQL)                  │
    └──────────────────────────────────────────────────────┘
"""

from .server import create_mcp_server, run_server

__all__ = [
    "create_mcp_server",
    "run_server",
]

__version__ = "0.1.0"
