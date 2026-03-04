#!/usr/bin/env python3
"""
MCP Gateway - Unified tool routing for BoTZ agents.

Routes tool calls to upstream MCP servers (n8n-agent, hostinger, cipher-memory,
e2b, vl-sentinel, docling) via a single endpoint on port 2091.

Also provides A2A (Agent-to-Agent) protocol endpoints:
- GET /.well-known/agent.json - Agent capability discovery
- POST /a2a/v1/tasks - JSON-RPC 2.0 task lifecycle management
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

import yaml

# Auth module for JWT validation
try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from mcp_bridge.auth import require_auth, check_query_token
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    require_auth = None
    check_query_token = None

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Metrics
if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter('mcp_gateway_requests_total', 'Total MCP gateway requests', ['method', 'endpoint'])
    REQUEST_LATENCY = Histogram('mcp_gateway_request_latency_seconds', 'MCP gateway request latency')
    TOOL_CALLS = Counter('mcp_gateway_tool_calls_total', 'Total tool calls', ['server', 'tool'])
else:
    # Fallback no-op metrics
    REQUEST_COUNT = None
    REQUEST_LATENCY = None
    TOOL_CALLS = None


def _track_latency():
    """Context manager for tracking request latency."""
    if REQUEST_LATENCY:
        return REQUEST_LATENCY.time()
    else:
        return _NoOpContext()


class _NoOpContext:
    """No-op context manager for when prometheus_client is not available."""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

# Import A2A module
try:
    from a2a import get_agent_card, TaskHandler
    A2A_AVAILABLE = True
except ImportError:
    A2A_AVAILABLE = False

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
    """HTTP request handler for MCP Gateway with A2A protocol support."""

    gateway = MCPGateway()

    # A2A components (initialized in main)
    a2a_task_handler: Optional['TaskHandler'] = None
    a2a_enabled: bool = A2A_AVAILABLE

    # Auth configuration
    auth_enabled: bool = AUTH_AVAILABLE and bool(os.environ.get('SUPABASE_JWT_SECRET', ''))

    # Endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        '/health', '/healthz', '/metrics',
        '/.well-known/agent.json',
        '/a2a/health', '/a2a/v1/health'
    }

    def _check_auth(self) -> tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Check authentication from Authorization header or query token.

        Returns:
            Tuple of (is_authenticated, payload, message)
        """
        if not self.auth_enabled:
            return True, None, "AUTH_DISABLED"

        # Try Authorization header first
        auth_header = self.headers.get('Authorization', '')
        if auth_header:
            return require_auth(auth_header)

        # Fallback to query parameter token
        if '?token=' in self.path or '&token=' in self.path:
            # Parse token from query string
            query_start = self.path.find('?')
            if query_start != -1:
                query_string = self.path[query_start + 1:]
                for param in query_string.split('&'):
                    if param.startswith('token='):
                        token = param[6:]
                        return check_query_token(token)

        return False, None, "NO_AUTH_PROVIDED"

    def _is_public_endpoint(self) -> bool:
        """Check if current path is a public endpoint."""
        path = self.path.split('?')[0]  # Strip query params
        return path in self.PUBLIC_ENDPOINTS

    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics labels (strip query strings, normalize dynamic segments)."""
        # Strip query strings
        path = path.split('?')[0]
        # Normalize dynamic task IDs
        if path.startswith('/a2a/v1/tasks/') and len(path.split('/')) > 4:
            return '/a2a/v1/tasks/{id}'
        # Normalize dynamic server names in /tools/{server}
        if path.startswith('/tools/') and len(path.split('/')) > 2:
            return '/tools/{server}'
        return path

    def _track_tool_call(self, tool_name: str) -> None:
        """Track tool call metrics."""
        if TOOL_CALLS and tool_name:
            server = tool_name.split(':')[0] if ':' in tool_name else 'unknown'
            TOOL_CALLS.labels(server, tool_name).inc()

    def _send_json(self, status: int, data: Dict):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _send_metrics(self):
        """Send Prometheus metrics."""
        if PROMETHEUS_AVAILABLE:
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(generate_latest())
        else:
            self.send_response(503)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Prometheus metrics not available (prometheus_client not installed)')

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests with latency tracking."""
        with _track_latency():
            # Standard PMOVES.AI healthz endpoint
            if self.path == '/healthz':
                self._send_json(200, {
                    "status": "healthy",
                    "service": "MCP Gateway",
                    "version": "2.0.0",
                    "upstream_servers": len(self.gateway.upstream_servers),
                    "a2a_enabled": self.a2a_enabled,
                    "prometheus_enabled": PROMETHEUS_AVAILABLE,
                })
                if REQUEST_COUNT:
                    REQUEST_COUNT.labels('GET', '/healthz').inc()
                return

            # Prometheus metrics endpoint
            if self.path == '/metrics':
                self._send_metrics()
                if REQUEST_COUNT:
                    REQUEST_COUNT.labels('GET', '/metrics').inc()
                return

            # A2A Agent Card discovery endpoint
            if self.path == '/.well-known/agent.json':
                if self.a2a_enabled:
                    tools = self.gateway.get_all_tools()
                    card = get_agent_card(self.gateway.upstream_servers, tools)
                    self._send_json(200, card.to_dict())
                else:
                    self._send_json(501, {"error": "A2A protocol not available"})
                if REQUEST_COUNT:
                    REQUEST_COUNT.labels('GET', '/.well-known/agent.json').inc()
                return

            # A2A health check
            if self.path == '/a2a/health' or self.path == '/a2a/v1/health':
                self._send_json(200, {
                    "status": "healthy" if self.a2a_enabled else "unavailable",
                    "service": "A2A Protocol",
                    "version": "1.0.0",
                    "enabled": self.a2a_enabled,
                })
                if REQUEST_COUNT:
                    REQUEST_COUNT.labels('GET', self.path).inc()
                return

            # A2A task info (GET)
            if self.path.startswith('/a2a/v1/tasks/') and self.a2a_task_handler:
                task_id = self.path.split('/')[4]
                result = self.a2a_task_handler.handle_jsonrpc({
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "params": {"task_id": task_id},
                    "id": 1,
                })
                status = 200 if "result" in result else 404
                self._send_json(status, result)
                if REQUEST_COUNT:
                    REQUEST_COUNT.labels('GET', '/a2a/v1/tasks/{id}').inc()
                return

            if self.path == '/health':
                self._send_json(200, {
                    "status": "healthy",
                    "service": "MCP Gateway",
                    "version": "2.0.0",
                    "upstream_servers": len(self.gateway.upstream_servers),
                    "a2a_enabled": self.a2a_enabled,
                    "auth_enabled": self.auth_enabled,
                })
                if REQUEST_COUNT:
                    REQUEST_COUNT.labels('GET', '/health').inc()

            elif self.path == '/servers':
                # Auth required for server listing
                is_auth, _, msg = self._check_auth()
                if not is_auth:
                    self._send_json(401, {"error": "Unauthorized", "detail": msg})
                    return
                servers = self.gateway.list_upstream_servers()
                self._send_json(200, {"servers": servers})
                if REQUEST_COUNT:
                    REQUEST_COUNT.labels('GET', '/servers').inc()

            elif self.path == '/tools':
                # Auth required for tool listing
                is_auth, _, msg = self._check_auth()
                if not is_auth:
                    self._send_json(401, {"error": "Unauthorized", "detail": msg})
                    return
                tools = self.gateway.get_all_tools()
                self._send_json(200, {
                    "tools": tools,
                    "count": len(tools)
                })
                if REQUEST_COUNT:
                    REQUEST_COUNT.labels('GET', '/tools').inc()

            elif self.path.startswith('/tools/'):
                # Auth required for server-specific tool listing
                is_auth, _, msg = self._check_auth()
                if not is_auth:
                    self._send_json(401, {"error": "Unauthorized", "detail": msg})
                    return
                server_name = self.path.split('/')[2]
                tools = self.gateway.get_tools_from_server(server_name)
                self._send_json(200, {
                    "server": server_name,
                    "tools": tools,
                    "count": len(tools)
                })
                if REQUEST_COUNT:
                    REQUEST_COUNT.labels('GET', '/tools/{server}').inc()

            else:
                self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests with latency tracking."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'

        # Normalize path for metrics
        normalized_path = self._normalize_path(self.path)

        # Track request
        if REQUEST_COUNT:
            REQUEST_COUNT.labels('POST', normalized_path).inc()

        with _track_latency():
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
                return

            # A2A JSON-RPC endpoint
            if self.path == '/a2a/v1/tasks' or self.path == '/a2a/tasks':
                if self.a2a_task_handler:
                    result = self.a2a_task_handler.handle_jsonrpc(data)
                    status = 200 if "result" in result else 400
                    self._send_json(status, result)
                else:
                    self._send_json(501, {"error": "A2A protocol not available"})
                return

            if self.path == '/call':
                # Auth required for tool calls
                is_auth, payload, msg = self._check_auth()
                if not is_auth:
                    self._send_json(401, {"error": "Unauthorized", "detail": msg})
                    return

                # Tool call endpoint
                tool_name = data.get('tool') or data.get('name')
                arguments = data.get('arguments', {})

                if not tool_name:
                    self._send_json(400, {"error": "Missing tool name"})
                    return

                # Track tool call metrics
                self._track_tool_call(tool_name)

                result = self.gateway.call_tool(tool_name, arguments)
                self._send_json(200, result)

            elif self.path == '/mcp':
                # Auth required for MCP JSON-RPC calls
                is_auth, payload, msg = self._check_auth()
                req_id = data.get('id', 1)

                if not is_auth:
                    self._send_json(401, {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32600, "message": f"Unauthorized: {msg}"}
                    })
                    return

                # MCP JSON-RPC endpoint
                method = data.get('method')
                params = data.get('params', {})

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

                    # Track tool call metrics
                    self._track_tool_call(tool_name)

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
    """Main entry point for MCP Gateway with A2A support."""
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '2091'))

    logger.info(f"Starting MCP Gateway on {host}:{port}")
    logger.info(f"Configured upstream servers: {list(MCP_UPSTREAM_SERVERS.keys())}")

    # Log JWT auth status
    jwt_secret = os.environ.get('SUPABASE_JWT_SECRET', '')
    if AUTH_AVAILABLE and jwt_secret:
        logger.info("JWT Authentication: Enabled (SUPABASE_JWT_SECRET configured)")
        logger.info("  - Protected: /call, /mcp, /tools, /servers")
        logger.info("  - Public: /health, /healthz, /metrics, /.well-known/agent.json")
    elif AUTH_AVAILABLE and not jwt_secret:
        logger.warning("JWT Authentication: Disabled (SUPABASE_JWT_SECRET not set)")
        logger.warning("  - All endpoints accessible without auth (development mode)")
    else:
        logger.warning("JWT Authentication: Unavailable (python-jose not installed)")

    # Log Prometheus metrics status
    if PROMETHEUS_AVAILABLE:
        logger.info("Prometheus Metrics: Enabled at /metrics")
    else:
        logger.warning("Prometheus Metrics: Disabled (prometheus_client not installed)")

    # Initialize A2A if available
    if A2A_AVAILABLE:
        logger.info("A2A Protocol: Enabled")
        logger.info("  - Agent Card: GET /.well-known/agent.json")
        logger.info("  - Tasks API:  POST /a2a/v1/tasks")

        # Create task handler with gateway's tool executor
        gateway_instance = GatewayHTTPHandler.gateway
        GatewayHTTPHandler.a2a_task_handler = TaskHandler(
            tool_executor=gateway_instance.call_tool
        )
    else:
        logger.warning("A2A Protocol: Disabled (module not found)")

    server = HTTPServer((host, port), GatewayHTTPHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down MCP Gateway...")
        if GatewayHTTPHandler.a2a_task_handler:
            GatewayHTTPHandler.a2a_task_handler.shutdown()
        server.shutdown()


if __name__ == "__main__":
    main()
