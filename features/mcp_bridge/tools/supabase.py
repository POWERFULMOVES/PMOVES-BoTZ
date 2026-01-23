"""
Supabase MCP Tools

MCP tools for Supabase database operations:
- supabase_query: Execute read queries via PostgREST
- supabase_insert: Insert records
- supabase_rpc: Call database functions
- supabase_health: Check connection

Usage:
    result = await handle_tool("supabase_query", {
        "table": "agent_sessions",
        "select": "id,agent_id,status",
        "filters": {"status": "eq.active"}
    })
"""

import json
import os
from typing import Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:3010")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")


# Tool definitions
TOOLS = [
    {
        "name": "supabase_query",
        "description": "Query Supabase table via PostgREST API",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "description": "Table name to query",
                },
                "select": {
                    "type": "string",
                    "description": "Columns to select (comma-separated, or * for all)",
                    "default": "*",
                },
                "filters": {
                    "type": "object",
                    "description": "PostgREST filters (e.g., {\"status\": \"eq.active\", \"created_at\": \"gt.2025-01-01\"})",
                },
                "order": {
                    "type": "string",
                    "description": "Order by column (e.g., 'created_at.desc')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum rows to return",
                    "default": 100,
                },
            },
            "required": ["table"],
        },
    },
    {
        "name": "supabase_insert",
        "description": "Insert record into Supabase table",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "description": "Table name",
                },
                "record": {
                    "type": "object",
                    "description": "Record to insert",
                },
                "upsert": {
                    "type": "boolean",
                    "description": "Upsert (update if exists)",
                    "default": False,
                },
            },
            "required": ["table", "record"],
        },
    },
    {
        "name": "supabase_rpc",
        "description": "Call Supabase RPC function",
        "inputSchema": {
            "type": "object",
            "properties": {
                "function": {
                    "type": "string",
                    "description": "Function name to call",
                },
                "params": {
                    "type": "object",
                    "description": "Function parameters",
                },
            },
            "required": ["function"],
        },
    },
    {
        "name": "supabase_tables",
        "description": "List available PMOVES Supabase tables",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "supabase_health",
        "description": "Check Supabase connection status",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# Common PMOVES tables
PMOVES_TABLES = {
    "pmoves_core": {
        "description": "Core PMOVES data",
        "tables": [
            "content_items",
            "transcripts",
            "summaries",
            "chapters",
        ],
    },
    "agent": {
        "description": "Agent state and sessions",
        "tables": [
            "agent_sessions",
            "agent_audit_logs",
            "agent_cost_metrics",
        ],
    },
    "archon": {
        "description": "Archon prompts and forms",
        "tables": [
            "prompts",
            "forms",
            "agent_configs",
        ],
    },
}


async def handle_tool(name: str, arguments: dict) -> dict:
    """
    Handle tool invocation.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result as MCP content block
    """
    if name == "supabase_tables":
        return _handle_tables()

    if not HAS_HTTPX:
        return {"content": [{"type": "text", "text": "Error: httpx not installed"}]}

    try:
        if name == "supabase_query":
            return await _handle_query(arguments)
        elif name == "supabase_insert":
            return await _handle_insert(arguments)
        elif name == "supabase_rpc":
            return await _handle_rpc(arguments)
        elif name == "supabase_health":
            return await _handle_health()
        else:
            return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


async def _handle_query(args: dict) -> dict:
    """Handle supabase_query tool."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        table = args["table"]
        params = {"select": args.get("select", "*")}

        # Add filters
        filters = args.get("filters", {})
        for key, value in filters.items():
            params[key] = value

        # Add ordering
        if "order" in args:
            params["order"] = args["order"]

        # Add limit
        params["limit"] = args.get("limit", 100)

        headers = {}
        if SUPABASE_KEY:
            headers["apikey"] = SUPABASE_KEY
            headers["Authorization"] = f"Bearer {SUPABASE_KEY}"

        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        results = response.json()

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(results, indent=2, default=str),
                }
            ]
        }


async def _handle_insert(args: dict) -> dict:
    """Handle supabase_insert tool."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        table = args["table"]
        record = args["record"]

        headers = {"Content-Type": "application/json"}
        if SUPABASE_KEY:
            headers["apikey"] = SUPABASE_KEY
            headers["Authorization"] = f"Bearer {SUPABASE_KEY}"

        if args.get("upsert"):
            headers["Prefer"] = "resolution=merge-duplicates"

        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            json=record,
            headers=headers,
        )
        response.raise_for_status()

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Inserted record into {table}",
                }
            ]
        }


async def _handle_rpc(args: dict) -> dict:
    """Handle supabase_rpc tool."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        function = args["function"]
        params = args.get("params", {})

        headers = {"Content-Type": "application/json"}
        if SUPABASE_KEY:
            headers["apikey"] = SUPABASE_KEY
            headers["Authorization"] = f"Bearer {SUPABASE_KEY}"

        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/rpc/{function}",
            json=params,
            headers=headers,
        )
        response.raise_for_status()
        result = response.json()

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, default=str),
                }
            ]
        }


async def _handle_health() -> dict:
    """Handle supabase_health tool."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            headers = {}
            if SUPABASE_KEY:
                headers["apikey"] = SUPABASE_KEY

            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/",
                headers=headers,
            )
            status = "healthy" if response.status_code in [200, 401] else "unhealthy"
        except Exception as e:
            status = f"offline: {str(e)}"

    return {
        "content": [
            {
                "type": "text",
                "text": f"Supabase Status: {status}\nEndpoint: {SUPABASE_URL}",
            }
        ]
    }


def _handle_tables() -> dict:
    """Handle supabase_tables tool."""
    output_lines = [
        "PMOVES Supabase Tables",
        "======================",
    ]

    for schema, info in PMOVES_TABLES.items():
        output_lines.append(f"\n## {schema}")
        output_lines.append(f"  {info['description']}")
        for table in info["tables"]:
            output_lines.append(f"  - {table}")

    output_lines.extend([
        "",
        "## Query Examples",
        "  {\"table\": \"content_items\", \"limit\": 10}",
        "  {\"table\": \"agent_sessions\", \"filters\": {\"status\": \"eq.active\"}}",
    ])

    return {
        "content": [
            {
                "type": "text",
                "text": "\n".join(output_lines),
            }
        ]
    }
