"""
Hi-RAG MCP Tools

MCP tools for Hi-RAG v2 hybrid knowledge retrieval:
- hirag_query: Full hybrid search with reranking
- hirag_similarity: Vector-only similarity search
- hirag_graph: Knowledge graph traversal
- hirag_health: Service health check

Usage:
    from pmoves_botz.features.mcp_bridge.tools.hirag import TOOLS

    # Register with MCP server
    for tool in TOOLS:
        server.register_tool(tool)
"""

import os
from typing import Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

HIRAG_URL = os.getenv("HIRAG_URL", "http://localhost:8086")


# Tool definitions
TOOLS = [
    {
        "name": "hirag_query",
        "description": "Query Hi-RAG v2 hybrid knowledge base with vector, graph, and full-text search",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 10,
                },
                "rerank": {
                    "type": "boolean",
                    "description": "Apply cross-encoder reranking",
                    "default": True,
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Limit to specific sources: vector, graph, fulltext",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "hirag_similarity",
        "description": "Vector-only similarity search for finding similar content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to find similar documents for",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results",
                    "default": 5,
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "hirag_graph",
        "description": "Query knowledge graph for entity relationships",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity": {
                    "type": "string",
                    "description": "Entity name to start traversal from",
                },
                "relationship": {
                    "type": "string",
                    "description": "Optional relationship type filter",
                },
                "depth": {
                    "type": "integer",
                    "description": "Traversal depth",
                    "default": 2,
                },
            },
            "required": ["entity"],
        },
    },
    {
        "name": "hirag_health",
        "description": "Check Hi-RAG service health status",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


async def handle_tool(name: str, arguments: dict) -> dict:
    """
    Handle tool invocation.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result as MCP content block
    """
    if not HAS_HTTPX:
        return {"content": [{"type": "text", "text": "Error: httpx not installed"}]}

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            if name == "hirag_query":
                return await _handle_query(client, arguments)
            elif name == "hirag_similarity":
                return await _handle_similarity(client, arguments)
            elif name == "hirag_graph":
                return await _handle_graph(client, arguments)
            elif name == "hirag_health":
                return await _handle_health(client)
            else:
                return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


async def _handle_query(client: httpx.AsyncClient, args: dict) -> dict:
    """Handle hirag_query tool."""
    payload = {
        "query": args["query"],
        "top_k": args.get("top_k", 10),
        "rerank": args.get("rerank", True),
    }
    if "sources" in args:
        payload["sources"] = args["sources"]

    response = await client.post(f"{HIRAG_URL}/hirag/query", json=payload)
    response.raise_for_status()

    results = response.json()
    return {
        "content": [
            {
                "type": "text",
                "text": _format_results(results),
            }
        ]
    }


async def _handle_similarity(client: httpx.AsyncClient, args: dict) -> dict:
    """Handle hirag_similarity tool."""
    payload = {
        "query": args["text"],
        "top_k": args.get("top_k", 5),
        "sources": ["vector"],
        "rerank": False,
    }

    response = await client.post(f"{HIRAG_URL}/hirag/query", json=payload)
    response.raise_for_status()

    results = response.json()
    return {
        "content": [
            {
                "type": "text",
                "text": _format_results(results),
            }
        ]
    }


async def _handle_graph(client: httpx.AsyncClient, args: dict) -> dict:
    """Handle hirag_graph tool."""
    # Graph queries go through Hi-RAG's graph endpoint if available
    # Falls back to direct Neo4j query
    payload = {
        "entity": args["entity"],
        "relationship": args.get("relationship"),
        "depth": args.get("depth", 2),
    }

    try:
        response = await client.post(f"{HIRAG_URL}/hirag/graph", json=payload)
        response.raise_for_status()
        results = response.json()
    except Exception:
        results = {"error": "Graph query endpoint not available"}

    return {
        "content": [
            {
                "type": "text",
                "text": str(results),
            }
        ]
    }


async def _handle_health(client: httpx.AsyncClient) -> dict:
    """Handle hirag_health tool."""
    try:
        response = await client.get(f"{HIRAG_URL}/healthz", timeout=5.0)
        status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        status = f"offline: {str(e)}"

    return {
        "content": [
            {
                "type": "text",
                "text": f"Hi-RAG Status: {status}",
            }
        ]
    }


def _format_results(results: dict) -> str:
    """Format search results for display."""
    output_lines = []

    if "results" in results:
        for i, result in enumerate(results["results"], 1):
            score = result.get("score", 0)
            content = result.get("content", result.get("text", ""))[:200]
            source = result.get("source", result.get("metadata", {}).get("source", "unknown"))

            output_lines.append(f"{i}. [{score:.3f}] {source}")
            output_lines.append(f"   {content}...")
            output_lines.append("")

    if not output_lines:
        return "No results found"

    return "\n".join(output_lines)
