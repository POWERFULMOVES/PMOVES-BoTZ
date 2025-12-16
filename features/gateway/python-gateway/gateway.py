#!/usr/bin/env python3
"""
MCP Gateway - Unified tool routing for BoTZ agents.

Routes tool calls to upstream MCP servers (n8n-agent, hostinger, cipher-memory,
e2b, vl-sentinel, docling) via a single endpoint on port 2091.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Upstream MCP server configurations
MCP_UPSTREAM_SERVERS = {
    "n8n-agent": {
        "transport": "stdio",
        "command": ["docker", "exec", "-i", "docker-compose-n8n-agent-1", "python", "app_n8n_agent.py"],
        "description": "n8n Workflow Automation Agent"
    },
    "hostinger": {
        "transport": "stdio",
        "command": ["docker", "exec", "-i", "docker-compose-hostinger-1", "hostinger-api-mcp"],
        "description": "Hostinger VPS/DNS/Domain Management"
    },
    "cipher-memory": {
        "transport": "http",
        "url": "http://cipher-memory:8081",
        "description": "Persistent Memory & Reasoning"
    },
    "e2b": {
        "transport": "http",
        "url": "http://e2b-runner:7071",
        "description": "E2B Code Sandbox"
    },
    "vl-sentinel": {
        "transport": "http",
        "url": "http://vl-sentinel:7072",
        "description": "Vision-Language Guidance"
    },
    "docling": {
        "transport": "sse",
        "url": "http://docling-mcp:3020/sse",
        "description": "Document Processing"
    },
}


class MCPGateway:
    """MCP Gateway that routes tool calls to upstream servers."""

    def __init__(self):
        self.upstream_servers = MCP_UPSTREAM_SERVERS

    def _call_stdio_server(self, command: List[str], request: Dict) -> Dict:
        """Call an MCP server via stdio transport."""
        try:
            proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            request_json = json.dumps(request) + "\n"
            stdout, stderr = proc.communicate(input=request_json, timeout=60)

            # Parse response - skip log lines
            for line in stdout.strip().split('\n'):
                if line.startswith('{'):
                    return json.loads(line)

            return {"error": f"No valid JSON response. stderr: {stderr[:500]}"}
        except subprocess.TimeoutExpired:
            proc.kill()
            return {"error": "Request timed out"}
        except Exception as e:
            return {"error": str(e)}

    def _call_http_server(self, url: str, request: Dict) -> Dict:
        """Call an MCP server via HTTP transport."""
        try:
            req = Request(
                url,
                data=json.dumps(request).encode(),
                headers={"Content-Type": "application/json"}
            )
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except URLError as e:
            return {"error": f"HTTP error: {e}"}
        except Exception as e:
            return {"error": str(e)}

    def list_upstream_servers(self) -> List[Dict[str, Any]]:
        """List all configured upstream MCP servers."""
        servers = []
        for name, config in self.upstream_servers.items():
            servers.append({
                "name": name,
                "transport": config["transport"],
                "description": config.get("description", ""),
                "status": "configured"
            })
        return servers

    def get_tools_from_server(self, server_name: str) -> List[Dict]:
        """Get tools from a specific upstream server."""
        if server_name not in self.upstream_servers:
            return []

        config = self.upstream_servers[server_name]
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        if config["transport"] == "stdio":
            response = self._call_stdio_server(config["command"], request)
        elif config["transport"] in ("http", "sse"):
            response = self._call_http_server(config["url"], request)
        else:
            return []

        if "result" in response and "tools" in response["result"]:
            tools = response["result"]["tools"]
            # Prefix tool names with server name for routing
            for tool in tools:
                tool["_server"] = server_name
                tool["qualified_name"] = f"{server_name}:{tool.get('name', tool.get('id', ''))}"
            return tools

        return []

    def get_all_tools(self) -> List[Dict]:
        """Get aggregated tools from all upstream servers."""
        all_tools = []
        for server_name in self.upstream_servers:
            try:
                tools = self.get_tools_from_server(server_name)
                all_tools.extend(tools)
                logger.info(f"Loaded {len(tools)} tools from {server_name}")
            except Exception as e:
                logger.warning(f"Failed to get tools from {server_name}: {e}")
        return all_tools

    def call_tool(self, qualified_name: str, arguments: Dict) -> Dict:
        """Call a tool on the appropriate upstream server."""
        # Parse qualified name (server:tool_name)
        if ":" in qualified_name:
            server_name, tool_name = qualified_name.split(":", 1)
        else:
            # Try to find the tool in any server
            tool_name = qualified_name
            server_name = None
            for sname in self.upstream_servers:
                tools = self.get_tools_from_server(sname)
                for tool in tools:
                    if tool.get("name") == tool_name or tool.get("id") == tool_name:
                        server_name = sname
                        break
                if server_name:
                    break

        if not server_name or server_name not in self.upstream_servers:
            return {"error": f"Server not found for tool: {qualified_name}"}

        config = self.upstream_servers[server_name]
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        if config["transport"] == "stdio":
            return self._call_stdio_server(config["command"], request)
        elif config["transport"] in ("http", "sse"):
            return self._call_http_server(config["url"], request)

        return {"error": f"Unsupported transport: {config['transport']}"}


class GatewayHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP Gateway."""

    gateway = MCPGateway()

    def _send_json(self, status: int, data: Dict):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            self._send_json(200, {
                "status": "healthy",
                "service": "MCP Gateway",
                "version": "2.0.0",
                "upstream_servers": len(self.gateway.upstream_servers)
            })

        elif self.path == '/servers':
            servers = self.gateway.list_upstream_servers()
            self._send_json(200, {"servers": servers})

        elif self.path == '/tools':
            tools = self.gateway.get_all_tools()
            self._send_json(200, {
                "tools": tools,
                "count": len(tools)
            })

        elif self.path.startswith('/tools/'):
            server_name = self.path.split('/')[2]
            tools = self.gateway.get_tools_from_server(server_name)
            self._send_json(200, {
                "server": server_name,
                "tools": tools,
                "count": len(tools)
            })

        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        if self.path == '/call':
            # Tool call endpoint
            tool_name = data.get('tool') or data.get('name')
            arguments = data.get('arguments', {})

            if not tool_name:
                self._send_json(400, {"error": "Missing tool name"})
                return

            result = self.gateway.call_tool(tool_name, arguments)
            self._send_json(200, result)

        elif self.path == '/mcp':
            # MCP JSON-RPC endpoint
            method = data.get('method')
            params = data.get('params', {})
            req_id = data.get('id', 1)

            if method == 'tools/list':
                tools = self.gateway.get_all_tools()
                self._send_json(200, {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": tools}
                })

            elif method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                result = self.gateway.call_tool(tool_name, arguments)
                self._send_json(200, {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result.get('result', result)
                })

            else:
                self._send_json(400, {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                })

        else:
            self._send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        """Log HTTP requests."""
        logger.info(f"{self.address_string()} - {format % args}")


def main():
    """Main entry point for MCP Gateway."""
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '2091'))

    logger.info(f"Starting MCP Gateway on {host}:{port}")
    logger.info(f"Configured upstream servers: {list(MCP_UPSTREAM_SERVERS.keys())}")

    server = HTTPServer((host, port), GatewayHTTPHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down MCP Gateway...")
        server.shutdown()


if __name__ == "__main__":
    main()
