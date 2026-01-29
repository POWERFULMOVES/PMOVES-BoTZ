"""
PMOVES MCP Bridge Server

Combined MCP server exposing all PMOVES services as tools.
Can be run standalone or integrated with Claude Agent SDK.

Tools Exposed:
- Hi-RAG: hirag_query, hirag_similarity, hirag_graph, hirag_health
- NATS: nats_publish, nats_request, nats_subjects, nats_health
- TensorZero: tensorzero_chat, tensorzero_embed, tensorzero_providers, tensorzero_health
- Supabase: supabase_query, supabase_insert, supabase_rpc, supabase_tables, supabase_health

Usage:
    # Run as standalone server
    python -m pmoves_botz.features.mcp_bridge.server

    # Or programmatically
    from pmoves_botz.features.mcp_bridge.server import create_mcp_server, run_server
    server = create_mcp_server()
    await run_server(server)

Protocol:
    Uses JSON-RPC over stdio for MCP communication.
"""

import asyncio
import json
import sys
import time
from typing import Any, Callable

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Metrics
if PROMETHEUS_AVAILABLE:
    MCP_REQUESTS = Counter('mcp_bridge_requests_total', 'Total MCP requests', ['method'])
    TOOL_CALLS = Counter('mcp_bridge_tool_calls_total', 'Total tool calls', ['tool'])
    REQUEST_LATENCY = Histogram('mcp_bridge_request_latency_seconds', 'MCP request latency')
else:
    MCP_REQUESTS = None
    TOOL_CALLS = None
    REQUEST_LATENCY = None


class _LatencyTracker:
    """Context manager for tracking request latency."""
    def __init__(self):
        self.start_time = None
        self.histogram = REQUEST_LATENCY

    def __enter__(self):
        if self.histogram:
            self.start_time = time.time()
        return self

    def __exit__(self, *args):
        if self.histogram and self.start_time is not None:
            self.histogram.observe(time.time() - self.start_time)

try:
    from .tools import hirag, nats, tensorzero, supabase
except ImportError:
    # When run directly, use absolute imports
    from tools import hirag, nats, tensorzero, supabase


class MCPServer:
    """
    Model Context Protocol server implementation.

    Exposes PMOVES services as MCP tools that can be used by
    any MCP-compatible client (Claude Agent SDK, Claude Code, etc.).

    Attributes:
        name: Server name for identification
        version: Server version
        tools: Registered tool definitions
        handlers: Tool handler functions
    """

    def __init__(self, name: str = "pmoves-mcp", version: str = "0.1.0"):
        """
        Initialize MCP server.

        Args:
            name: Server name
            version: Server version
        """
        self.name = name
        self.version = version
        self.tools: list[dict] = []
        self.handlers: dict[str, Callable] = {}

    def register_tool(self, tool_def: dict, handler: Callable) -> None:
        """
        Register a tool with the server.

        Args:
            tool_def: Tool definition (name, description, inputSchema)
            handler: Async function to handle tool calls
        """
        self.tools.append(tool_def)
        self.handlers[tool_def["name"]] = handler

    def register_tools_from_module(self, module: Any, handler: Callable) -> None:
        """
        Register all tools from a module.

        Args:
            module: Module with TOOLS list
            handler: Handler function for the module's tools
        """
        for tool_def in getattr(module, "TOOLS", []):
            self.register_tool(tool_def, handler)

    async def handle_request(self, request: dict) -> dict:
        """
        Handle an incoming MCP request.

        Args:
            request: JSON-RPC request

        Returns:
            JSON-RPC response
        """
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        # Track request
        if MCP_REQUESTS:
            MCP_REQUESTS.labels(method).inc()

        with _LatencyTracker():
            try:
                if method == "initialize":
                    result = await self._handle_initialize(params)
                elif method == "tools/list":
                    result = await self._handle_tools_list()
                elif method == "tools/call":
                    result = await self._handle_tools_call(params)
                    # Track tool call
                    if TOOL_CALLS:
                        tool_name = params.get("name", "unknown")
                        TOOL_CALLS.labels(tool_name).inc()
                elif method == "ping":
                    result = {"pong": True}
                else:
                    return self._error_response(request_id, -32601, f"Unknown method: {method}")

                return self._success_response(request_id, result)

            except Exception as e:
                return self._error_response(request_id, -32603, str(e))

    async def _handle_initialize(self, params: dict) -> dict:
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
        }

    async def _handle_tools_list(self) -> dict:
        """Handle tools/list request."""
        return {"tools": self.tools}

    async def _handle_tools_call(self, params: dict) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in self.handlers:
            raise ValueError(f"Unknown tool: {tool_name}")

        handler = self.handlers[tool_name]
        result = await handler(tool_name, arguments)

        return result

    def _success_response(self, request_id: Any, result: dict) -> dict:
        """Build success response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    def _error_response(self, request_id: Any, code: int, message: str) -> dict:
        """Build error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }


def create_mcp_server() -> MCPServer:
    """
    Create and configure the PMOVES MCP server.

    Returns:
        Configured MCPServer instance with all tools registered
    """
    server = MCPServer(name="pmoves-mcp", version="0.1.0")

    # Register Hi-RAG tools
    server.register_tools_from_module(hirag, hirag.handle_tool)

    # Register NATS tools
    server.register_tools_from_module(nats, nats.handle_tool)

    # Register TensorZero tools
    server.register_tools_from_module(tensorzero, tensorzero.handle_tool)

    # Register Supabase tools
    server.register_tools_from_module(supabase, supabase.handle_tool)

    return server


async def run_server(server: MCPServer) -> None:
    """
    Run MCP server over stdio.

    Args:
        server: Configured MCPServer instance
    """
    # Read from stdin, write to stdout
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(
        lambda: protocol, sys.stdin
    )

    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())

    # Process requests
    while True:
        try:
            # Read content-length header
            header_line = await reader.readline()
            if not header_line:
                break

            # Skip empty lines
            if header_line.strip() == b"":
                continue

            # Parse content length
            if header_line.startswith(b"Content-Length:"):
                content_length = int(header_line.split(b":")[1].strip())

                # Read separator
                await reader.readline()

                # Read content
                content = await reader.read(content_length)
                request = json.loads(content.decode())

                # Handle request
                response = await server.handle_request(request)

                # Write response
                response_bytes = json.dumps(response).encode()
                response_header = f"Content-Length: {len(response_bytes)}\r\n\r\n"
                writer.write(response_header.encode() + response_bytes)
                await writer.drain()

        except asyncio.CancelledError:
            break
        except Exception as e:
            # Log error but continue
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()


async def run_http_server(server: MCPServer, host: str = "0.0.0.0", port: int = 8100) -> None:
    """
    Run MCP server over HTTP (alternative transport).

    Args:
        server: Configured MCPServer instance
        host: Bind host
        port: Bind port
    """
    try:
        from aiohttp import web
    except ImportError:
        print("Error: aiohttp required for HTTP server. Install with: pip install aiohttp")
        return

    async def handle_post(request: web.Request) -> web.Response:
        """Handle POST /mcp requests."""
        try:
            data = await request.json()
            response = await server.handle_request(data)
            return web.json_response(response)
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500,
            )

    async def handle_health(request: web.Request) -> web.Response:
        """Health check endpoint."""
        # Import here to avoid import errors if module not available
        try:
            from .utils.integration_health import IntegrationHealth
            health_check = IntegrationHealth()
            integrations = await health_check.get_status()

            all_healthy = all(integration["healthy"] for integration in integrations.values())
            status = "healthy" if all_healthy else "degraded"

            return web.json_response({
                "status": status,
                "server": server.name,
                "version": server.version,
                "tools_count": len(server.tools),
                "prometheus_enabled": PROMETHEUS_AVAILABLE,
                "integrations": integrations,
            })
        except Exception as e:
            # If integration health checks fail, return degraded status
            return web.json_response({
                "status": "degraded",
                "server": server.name,
                "version": server.version,
                "tools_count": len(server.tools),
                "prometheus_enabled": PROMETHEUS_AVAILABLE,
                "error": f"Integration health check failed: {str(e)}",
            })

    async def handle_metrics(_request: web.Request) -> web.Response:
        """Prometheus metrics endpoint."""
        if PROMETHEUS_AVAILABLE:
            metrics = generate_latest()
            return web.Response(body=metrics, content_type=CONTENT_TYPE_LATEST)
        else:
            return web.json_response(
                {"error": "Prometheus metrics not available"},
                status=503
            )

    app = web.Application()
    app.router.add_post("/mcp", handle_post)
    app.router.add_get("/healthz", handle_health)
    app.router.add_get("/metrics", handle_metrics)
    app.router.add_get("/tools", lambda r: web.json_response({"tools": server.tools}))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    print(f"PMOVES MCP Server running at http://{host}:{port}")
    print(f"Tools available: {len(server.tools)}")

    # Check integration health at startup
    try:
        from .utils.integration_health import IntegrationHealth
        health_check = IntegrationHealth()
        integrations = await health_check.get_status()

        print("[STARTUP] Integration Status:")
        for name, status in integrations.items():
            health_str = "✓" if status["healthy"] else "✗"
            print(f"  {health_str} {name}: {status['url']}")
    except Exception as e:
        print(f"[STARTUP] Integration health check failed: {e}")

    # Keep running
    await asyncio.Event().wait()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="PMOVES MCP Bridge Server")
    parser.add_argument("--http", action="store_true", help="Run as HTTP server instead of stdio")
    parser.add_argument("--port", type=int, default=8100, help="HTTP port (default: 8100)")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")

    args = parser.parse_args()

    server = create_mcp_server()

    if args.http:
        asyncio.run(run_http_server(server, args.host, args.port))
    else:
        asyncio.run(run_server(server))


if __name__ == "__main__":
    main()
