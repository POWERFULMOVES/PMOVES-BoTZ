#!/usr/bin/env python3
"""
PMOVES n8n Agent - MCP Server for n8n Workflow Automation

Provides full n8n workflow control via MCP protocol with cipher-memory
integration for skills storage, documentation, and reasoning traces.

Transport: stdio (default) or HTTP
Port: 7074 (when running HTTP mode)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from typing import Any, Dict, List, Optional

import httpx
from mcp import Tool
from mcp.server import Server
from mcp.types import CallToolResult, TextContent
import mcp.server.stdio


class N8nClient:
    """HTTP client for n8n REST API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "X-N8N-API-KEY": api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to n8n API."""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                json=data,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def list_workflows(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List all workflows."""
        params = {"active": "true"} if active_only else {}
        result = await self._request("GET", "/workflows", params=params)
        return result.get("data", [])

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow by ID."""
        return await self._request("GET", f"/workflows/{workflow_id}")

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow."""
        return await self._request("POST", "/workflows", data=workflow_data)

    async def update_workflow(
        self, workflow_id: str, workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing workflow."""
        return await self._request("PUT", f"/workflows/{workflow_id}", data=workflow_data)

    async def delete_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Delete a workflow."""
        return await self._request("DELETE", f"/workflows/{workflow_id}")

    async def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Activate a workflow."""
        return await self._request("POST", f"/workflows/{workflow_id}/activate")

    async def deactivate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Deactivate a workflow."""
        return await self._request("POST", f"/workflows/{workflow_id}/deactivate")

    async def execute_workflow(
        self, workflow_id: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a workflow with optional input data."""
        return await self._request(
            "POST", f"/workflows/{workflow_id}/run", data=data or {}
        )

    async def get_executions(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 10,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get execution history."""
        params: Dict[str, Any] = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        result = await self._request("GET", "/executions", params=params)
        return result.get("data", [])

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Get execution details."""
        return await self._request("GET", f"/executions/{execution_id}")


class CipherMemoryClient:
    """Client for cipher-memory MCP server integration."""

    def __init__(self, cipher_path: Optional[str] = None) -> None:
        self.cipher_path = cipher_path or os.environ.get(
            "CIPHER_MEMORY_PATH", "/app/features/cipher/pmoves_cipher"
        )
        self.cipher_binary = f"{self.cipher_path}/dist/src/app/index.cjs"

    def _run_cipher(self, prompt: str) -> str:
        """Run cipher CLI command."""
        if not os.path.exists(self.cipher_binary):
            return f"[cipher unavailable] {prompt}"

        try:
            cmd = ["node", self.cipher_binary, "--mode", "cli", prompt]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=os.environ.copy(),
            )
            return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
        except Exception as e:
            return f"[cipher error] {e}"

    def store_workflow_doc(
        self, workflow_name: str, description: str, tags: List[str]
    ) -> str:
        """Store workflow documentation in cipher memory."""
        prompt = f"""Store this workflow documentation:
Name: {workflow_name}
Description: {description}
Tags: {', '.join(tags)}
Type: n8n_workflow"""
        return self._run_cipher(prompt)

    def search_skills(self, query: str, limit: int = 5) -> str:
        """Search for automation skills/patterns."""
        prompt = f"Search for automation patterns related to: {query} (limit: {limit})"
        return self._run_cipher(prompt)

    def store_reasoning(
        self, task: str, workflow_chosen: str, reasoning: str, outcome: str
    ) -> str:
        """Store reasoning for workflow selection."""
        prompt = f"""Store reasoning trace:
Task: {task}
Workflow Chosen: {workflow_chosen}
Reasoning: {reasoning}
Outcome: {outcome}
Type: n8n_reasoning"""
        return self._run_cipher(prompt)

    def suggest_workflow(self, task_description: str) -> str:
        """Get workflow suggestion based on task."""
        prompt = f"Based on past automation patterns, suggest the best n8n workflow for: {task_description}"
        return self._run_cipher(prompt)


class N8nAgentServer:
    """MCP server for n8n workflow automation with cipher integration."""

    def __init__(self) -> None:
        self.server = Server("pmoves-n8n-agent")
        self.n8n = N8nClient(
            base_url=os.environ.get("N8N_API_URL", "http://n8n:5678/api/v1"),
            api_key=os.environ.get("N8N_API_KEY", ""),
        )
        self.cipher = CipherMemoryClient()

    def setup_handlers(self) -> None:
        """Setup MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                # n8n Workflow Management Tools
                Tool(
                    name="n8n_list_workflows",
                    description="List all n8n workflows with their status and metadata",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "active_only": {
                                "type": "boolean",
                                "default": False,
                                "description": "Only return active workflows",
                            }
                        },
                    },
                ),
                Tool(
                    name="n8n_get_workflow",
                    description="Get detailed workflow definition by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow ID",
                            }
                        },
                        "required": ["workflow_id"],
                    },
                ),
                Tool(
                    name="n8n_execute_workflow",
                    description="Execute an n8n workflow by ID with optional input data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow ID to execute",
                            },
                            "input_data": {
                                "type": "object",
                                "description": "Optional input data for the workflow",
                                "default": {},
                            },
                        },
                        "required": ["workflow_id"],
                    },
                ),
                Tool(
                    name="n8n_create_workflow",
                    description="Create a new n8n workflow from JSON definition",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Workflow name",
                            },
                            "nodes": {
                                "type": "array",
                                "description": "Array of workflow nodes",
                            },
                            "connections": {
                                "type": "object",
                                "description": "Node connections",
                            },
                            "active": {
                                "type": "boolean",
                                "default": False,
                                "description": "Activate workflow after creation",
                            },
                        },
                        "required": ["name", "nodes", "connections"],
                    },
                ),
                Tool(
                    name="n8n_update_workflow",
                    description="Update an existing n8n workflow",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow ID to update",
                            },
                            "workflow_data": {
                                "type": "object",
                                "description": "Updated workflow data",
                            },
                        },
                        "required": ["workflow_id", "workflow_data"],
                    },
                ),
                Tool(
                    name="n8n_delete_workflow",
                    description="Delete an n8n workflow by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow ID to delete",
                            }
                        },
                        "required": ["workflow_id"],
                    },
                ),
                Tool(
                    name="n8n_toggle_workflow",
                    description="Activate or deactivate an n8n workflow",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow ID",
                            },
                            "active": {
                                "type": "boolean",
                                "description": "True to activate, False to deactivate",
                            },
                        },
                        "required": ["workflow_id", "active"],
                    },
                ),
                Tool(
                    name="n8n_get_executions",
                    description="Get workflow execution history",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "Filter by workflow ID (optional)",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 10,
                                "description": "Max executions to return",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["success", "error", "waiting"],
                                "description": "Filter by status",
                            },
                        },
                    },
                ),
                # Cipher-Enhanced Tools
                Tool(
                    name="n8n_store_workflow_doc",
                    description="Store workflow documentation in cipher memory for future reference",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_name": {
                                "type": "string",
                                "description": "Name of the workflow",
                            },
                            "description": {
                                "type": "string",
                                "description": "What the workflow does and when to use it",
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": ["n8n", "automation"],
                                "description": "Tags for categorization",
                            },
                        },
                        "required": ["workflow_name", "description"],
                    },
                ),
                Tool(
                    name="n8n_search_skills",
                    description="Search cipher memory for automation patterns and workflow skills",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "What automation pattern to search for",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 5,
                                "description": "Max results to return",
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="n8n_suggest_workflow",
                    description="Use cipher reasoning to suggest the best workflow for a task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_description": {
                                "type": "string",
                                "description": "Description of what you want to automate",
                            }
                        },
                        "required": ["task_description"],
                    },
                ),
                Tool(
                    name="n8n_learn_from_execution",
                    description="Store execution results and reasoning in cipher memory for learning",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "description": "The task that was automated",
                            },
                            "workflow_name": {
                                "type": "string",
                                "description": "Workflow that was used",
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why this workflow was chosen",
                            },
                            "outcome": {
                                "type": "string",
                                "enum": ["success", "failure", "partial"],
                                "description": "Result of the execution",
                            },
                        },
                        "required": ["task", "workflow_name", "reasoning", "outcome"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            try:
                result = await self._handle_tool(name, arguments)
                return CallToolResult(
                    content=[TextContent(type="text", text=result)],
                    isError=False,
                )
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {e}")],
                    isError=True,
                )

    async def _handle_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Handle tool calls."""
        # n8n Workflow Tools
        if name == "n8n_list_workflows":
            workflows = await self.n8n.list_workflows(args.get("active_only", False))
            return json.dumps(
                [
                    {
                        "id": w.get("id"),
                        "name": w.get("name"),
                        "active": w.get("active"),
                        "createdAt": w.get("createdAt"),
                        "updatedAt": w.get("updatedAt"),
                    }
                    for w in workflows
                ],
                indent=2,
            )

        if name == "n8n_get_workflow":
            workflow = await self.n8n.get_workflow(args["workflow_id"])
            return json.dumps(workflow, indent=2)

        if name == "n8n_execute_workflow":
            result = await self.n8n.execute_workflow(
                args["workflow_id"], args.get("input_data", {})
            )
            return json.dumps(result, indent=2)

        if name == "n8n_create_workflow":
            workflow_data = {
                "name": args["name"],
                "nodes": args["nodes"],
                "connections": args["connections"],
                "active": args.get("active", False),
            }
            result = await self.n8n.create_workflow(workflow_data)
            # Store in cipher memory
            self.cipher.store_workflow_doc(
                args["name"],
                f"Created workflow with {len(args['nodes'])} nodes",
                ["n8n", "automation", "new"],
            )
            return json.dumps(result, indent=2)

        if name == "n8n_update_workflow":
            result = await self.n8n.update_workflow(
                args["workflow_id"], args["workflow_data"]
            )
            return json.dumps(result, indent=2)

        if name == "n8n_delete_workflow":
            result = await self.n8n.delete_workflow(args["workflow_id"])
            return json.dumps(result, indent=2)

        if name == "n8n_toggle_workflow":
            if args["active"]:
                result = await self.n8n.activate_workflow(args["workflow_id"])
            else:
                result = await self.n8n.deactivate_workflow(args["workflow_id"])
            return json.dumps(result, indent=2)

        if name == "n8n_get_executions":
            executions = await self.n8n.get_executions(
                workflow_id=args.get("workflow_id"),
                limit=args.get("limit", 10),
                status=args.get("status"),
            )
            return json.dumps(executions, indent=2)

        # Cipher-Enhanced Tools
        if name == "n8n_store_workflow_doc":
            result = self.cipher.store_workflow_doc(
                args["workflow_name"],
                args["description"],
                args.get("tags", ["n8n", "automation"]),
            )
            return f"Stored documentation for '{args['workflow_name']}': {result}"

        if name == "n8n_search_skills":
            result = self.cipher.search_skills(args["query"], args.get("limit", 5))
            return f"Search results for '{args['query']}':\n{result}"

        if name == "n8n_suggest_workflow":
            result = self.cipher.suggest_workflow(args["task_description"])
            return f"Workflow suggestion for '{args['task_description']}':\n{result}"

        if name == "n8n_learn_from_execution":
            result = self.cipher.store_reasoning(
                args["task"],
                args["workflow_name"],
                args["reasoning"],
                args["outcome"],
            )
            return f"Stored learning: {result}"

        return f"Unknown tool: {name}"


async def run_stdio_server(server: N8nAgentServer) -> None:
    """Run MCP server over stdio."""
    server.setup_handlers()
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options(),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="PMOVES n8n Agent MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    _ = parser.parse_args()

    server = N8nAgentServer()
    asyncio.run(run_stdio_server(server))


if __name__ == "__main__":
    main()
