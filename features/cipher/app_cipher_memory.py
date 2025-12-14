#!/usr/bin/env python3
"""
PMOVES Cipher Memory Integration Layer

Runs an MCP server that proxies “memory” operations into the bundled
Pmoves-cipher Node.js CLI (built into the image).

Default transport is stdio (MCP SDK), which is appropriate for MCP clients.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import Tool
from mcp.server import Server
from mcp.types import CallToolResult, TextContent
import mcp.server.stdio


class CipherMemoryManager:
    """Thin wrapper around the Pmoves-cipher CLI."""

    def __init__(self, cipher_path: Optional[str] = None) -> None:
        self.cipher_path = Path(cipher_path) if cipher_path else Path(__file__).parent / "pmoves_cipher"
        self.cipher_binary = self.cipher_path / "dist" / "src" / "app" / "index.cjs"
        self.config_path = self.cipher_path / "memAgent" / "cipher_pmoves.yml"
        self._temp_dir: Optional[str] = None

    def _ensure_cipher_built(self) -> None:
        if self.cipher_binary.exists():
            return
        raise RuntimeError(f"Cipher binary not found at {self.cipher_binary}. Image build likely failed.")

    def _create_temp_config(self, config_overrides: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if not config_overrides:
            return None

        base_path = Path(os.environ.get("CIPHER_CONFIG_PATH", str(self.config_path)))
        if not base_path.exists():
            raise RuntimeError(f"Cipher config not found at {base_path}")

        self._temp_dir = tempfile.mkdtemp(prefix="pmoves_cipher_")
        config = base_path.read_text()

        for key, value in config_overrides.items():
            if key == "llm_provider":
                config = config.replace("provider: openai", f"provider: {value}")
            elif key == "llm_model":
                config = config.replace("model: gpt-4.1-mini", f"model: {value}")
            elif key == "api_key":
                config = config.replace("apiKey: $OPENAI_API_KEY", f"apiKey: {value}")

        temp_config_path = Path(self._temp_dir) / "cipher.yml"
        temp_config_path.write_text(config)
        return str(temp_config_path)

    def _run_cipher_command(self, args: List[str], input_data: Optional[str] = None) -> str:
        self._ensure_cipher_built()

        env = os.environ.copy()
        try:
            cmd = ["node", str(self.cipher_binary)] + args
            result = subprocess.run(
                cmd,
                input=input_data,
                text=True,
                capture_output=True,
                env=env,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"Cipher exited {result.returncode}")
            return result.stdout
        finally:
            if self._temp_dir and os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None

    def store_memory(self, content: str, memory_type: str = "knowledge", session_id: str = "pmoves_default") -> str:
        _ = (memory_type, session_id)  # reserved for future cipher schema routing
        return self._run_cipher_command(["--mode", "cli", content]).strip()

    def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        output = self._run_cipher_command(["--mode", "cli", f"Search memory for: {query}"]).strip()
        results: List[Dict[str, Any]] = []
        for line in output.splitlines():
            if not line.strip():
                continue
            results.append({"content": line.strip(), "type": "knowledge", "relevance": 1.0})
            if len(results) >= limit:
                break
        return results

    def extract_and_operate_memory(self, content: str, operation: str = "add") -> str:
        return self._run_cipher_command(["--mode", "cli", f"Extract and {operation} this knowledge: {content}"]).strip()

    def store_reasoning_memory(self, reasoning: str, context: str = "") -> str:
        return self._run_cipher_command(["--mode", "cli", f"Store reasoning: {reasoning}\nContext: {context}"]).strip()

    def search_reasoning_patterns(self, query: str) -> List[Dict[str, Any]]:
        output = self._run_cipher_command(["--mode", "cli", f"Search reasoning patterns for: {query}"]).strip()
        patterns: List[Dict[str, Any]] = []
        for line in output.splitlines():
            if not line.strip():
                continue
            patterns.append({"pattern": line.strip(), "type": "reasoning"})
        return patterns


class CipherMemoryServer:
    """MCP server wrapper for CipherMemoryManager."""

    def __init__(self) -> None:
        self.server = Server("pmoves-cipher-memory")
        self.memory = CipherMemoryManager()

    def setup_handlers(self) -> None:
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="cipher_store_memory",
                    description="Store memory using Pmoves-cipher",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "memory_type": {"type": "string", "default": "knowledge"},
                            "session_id": {"type": "string", "default": "pmoves_default"},
                        },
                        "required": ["content"],
                    },
                ),
                Tool(
                    name="cipher_search_memory",
                    description="Search memory using Pmoves-cipher",
                    inputSchema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="cipher_extract_and_operate_memory",
                    description="Extract knowledge and apply an operation using Pmoves-cipher",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "operation": {"type": "string", "default": "add"},
                        },
                        "required": ["content"],
                    },
                ),
                Tool(
                    name="cipher_store_reasoning_memory",
                    description="Store reasoning steps using Pmoves-cipher",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "reasoning": {"type": "string"},
                            "context": {"type": "string", "default": ""},
                        },
                        "required": ["reasoning"],
                    },
                ),
                Tool(
                    name="cipher_search_reasoning_patterns",
                    description="Search reasoning patterns using Pmoves-cipher",
                    inputSchema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            try:
                if name == "cipher_store_memory":
                    out = self.memory.store_memory(
                        arguments["content"],
                        arguments.get("memory_type", "knowledge"),
                        arguments.get("session_id", "pmoves_default"),
                    )
                    return CallToolResult(content=[TextContent(type="text", text=out)], isError=False)
                if name == "cipher_search_memory":
                    res = self.memory.search_memory(arguments["query"], int(arguments.get("limit", 10)))
                    return CallToolResult(content=[TextContent(type="text", text=str(res))], isError=False)
                if name == "cipher_extract_and_operate_memory":
                    out = self.memory.extract_and_operate_memory(arguments["content"], arguments.get("operation", "add"))
                    return CallToolResult(content=[TextContent(type="text", text=out)], isError=False)
                if name == "cipher_store_reasoning_memory":
                    out = self.memory.store_reasoning_memory(arguments["reasoning"], arguments.get("context", ""))
                    return CallToolResult(content=[TextContent(type="text", text=out)], isError=False)
                if name == "cipher_search_reasoning_patterns":
                    res = self.memory.search_reasoning_patterns(arguments["query"])
                    return CallToolResult(content=[TextContent(type="text", text=str(res))], isError=False)
                return CallToolResult(content=[TextContent(type="text", text=f"Unknown tool: {name}")], isError=True)
            except Exception as e:
                return CallToolResult(content=[TextContent(type="text", text=f"Error: {e}")], isError=True)


async def run_stdio_server(server: CipherMemoryServer) -> None:
    server.setup_handlers()
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options(),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="PMOVES Cipher Memory MCP Server")
    parser.add_argument("--transport", choices=["stdio"], default="stdio")
    _ = parser.parse_args()

    server = CipherMemoryServer()
    asyncio.run(run_stdio_server(server))


if __name__ == "__main__":
    main()

