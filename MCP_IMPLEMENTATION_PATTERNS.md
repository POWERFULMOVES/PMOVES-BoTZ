# MCP Server Implementation Patterns

## Overview

This document provides official MCP (Model Context Protocol) server implementation patterns following the MCP 1.0+ specification. These patterns ensure proper HTTP transport, streaming support, and protocol compliance.

## Official MCP Documentation Reference

- **MCP Specification**: https://modelcontextprotocol.io/specification
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Transport Documentation**: https://modelcontextprotocol.io/specification/transports

## Core Implementation Patterns

### 1. Basic MCP Server Structure

```python
#!/usr/bin/env python3
"""
MCP Server implementation following official patterns.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

# MCP imports following official patterns
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
    ErrorData,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPServer:
    """Base MCP server implementation following official patterns."""
    
    def __init__(self, name: str):
        self.server = Server(name)
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup MCP server handlers following official patterns."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available tools - official pattern."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="example_tool",
                        description="Example tool implementation",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_param": {
                                    "type": "string",
                                    "description": "Example input parameter"
                                }
                            },
                            "required": ["input_param"]
                        }
                    )
                ]
            )
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls - official pattern."""
            try:
                if name == "example_tool":
                    input_param = arguments.get("input_param")
                    if not input_param:
                        return CallToolResult(
                            content=[TextContent(type="text", text="Error: input_param is required")],
                            isError=True
                        )
                    
                    # Tool implementation
                    result = f"Processed: {input_param}"
                    return CallToolResult(
                        content=[TextContent(type="text", text=result)],
                        isError=False
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                        isError=True
                    )
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
```

### 2. STDIO Transport Implementation

```python
async def run_stdio_server(server: MCPServer):
    """STDIO transport implementation - official pattern."""
    logger.info("Starting MCP Server with STDIO transport...")
    
    try:
        # Official STDIO pattern
        async with stdio_server() as (read_stream, write_stream):
            await server.server.run(
                read_stream,
                write_stream,
                server.server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Error running STDIO server: {e}")
        raise
```

### 3. HTTP Transport with SSE Implementation

```python
import asyncio
from aiohttp import web
from mcp.server.sse import SseServerTransport

async def run_http_server(server: MCPServer, host: str = "0.0.0.0", port: int = 3020):
    """HTTP transport with SSE - official pattern."""
    logger.info(f"Starting MCP Server with HTTP transport on {host}:{port}...")
    
    # Create SSE transport with proper configuration
    sse_transport = SseServerTransport(f"http://{host}:{port}/mcp")
    
    # Create aiohttp application
    app = web.Application()
    
    # Add SSE endpoint
    app.router.add_get("/mcp", sse_transport.handle_request)
    
    # Add health check endpoint
    async def health_check(request):
        return web.Response(text="OK", status=200)
    app.router.add_get("/health", health_check)
    
    # Configure CORS for browser clients
    app.router.add_options("/mcp", lambda req: web.Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept",
        }
    ))
    
    # Start server with proper session handling
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    
    await site.start()
    logger.info(f"HTTP server started on {host}:{port}")
    
    # Handle MCP sessions
    async def handle_session(session_streams):
        read_stream, write_stream = session_streams
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )
    
    # Set up session handler for SSE transport
    sse_transport.handle_session = handle_session
    
    # Keep server running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        await runner.cleanup()
```

### 4. Advanced HTTP Transport with Multiple Endpoints

```python
from aiohttp import web, WSMsgType
import json

class AdvancedMCPServer:
    """Advanced MCP server with multiple transport options."""
    
    def __init__(self, name: str):
        self.server = Server(name)
        self.setup_handlers()
        self.active_sessions = {}
    
    async def handle_websocket(self, request):
        """WebSocket transport handler."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Create streams for WebSocket
        # This is a simplified example - actual implementation would need
        # proper stream adapters for WebSocket
        
        session_id = id(ws)
        self.active_sessions[session_id] = ws
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    # Handle incoming MCP messages
                    data = json.loads(msg.data)
                    # Process message and send response
                    response = await self.process_mcp_message(data)
                    await ws.send_str(json.dumps(response))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
        finally:
            del self.active_sessions[session_id]
        
        return ws
    
    async def handle_sse(self, request):
        """Server-Sent Events handler."""
        response = web.StreamResponse()
        response.headers.update({
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        })
        await response.prepare(request)
        
        # Send initial SSE connection event
        await response.write(b'data: {"type": "connected"}\n\n')
        
        try:
            # Handle SSE session
            async for event in self.generate_sse_events():
                await response.write(f'data: {json.dumps(event)}\n\n'.encode())
        except Exception as e:
            logger.error(f"SSE error: {e}")
        finally:
            await response.write(b'data: {"type": "disconnected"}\n\n')
        
        return response
    
    async def generate_sse_events(self):
        """Generate SSE events for MCP communication."""
        # This would be implemented based on MCP protocol
        # For now, yield a keepalive event
        while True:
            yield {"type": "keepalive", "timestamp": asyncio.get_event_loop().time()}
            await asyncio.sleep(30)

async def run_advanced_http_server(server: AdvancedMCPServer, host: str = "0.0.0.0", port: int = 3020):
    """Advanced HTTP server with multiple transport options."""
    app = web.Application()
    
    # Add multiple transport endpoints
    app.router.add_get("/mcp/sse", server.handle_sse)
    app.router.add_get("/mcp/ws", server.handle_websocket)
    app.router.add_get("/health", lambda req: web.Response(text="OK"))
    
    # Add CORS handling
    app.router.add_options("/mcp/{path:.*}", lambda req: web.Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept, Authorization",
        }
    ))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Advanced HTTP server started on {host}:{port}")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Server stopped")
    finally:
        await runner.cleanup()
```

### 5. Error Handling Patterns

```python
from mcp.types import ErrorData

class RobustMCPServer:
    """MCP server with comprehensive error handling."""
    
    def __init__(self, name: str):
        self.server = Server(name)
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup handlers with proper error handling."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List tools with error handling."""
            try:
                tools = self.get_available_tools()
                return ListToolsResult(tools=tools)
            except Exception as e:
                logger.error(f"Error listing tools: {e}")
                # Return empty list on error rather than failing
                return ListToolsResult(tools=[])
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Call tools with comprehensive error handling."""
            try:
                # Validate input
                if not name:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Error: Tool name is required")],
                        isError=True
                    )
                
                # Execute tool with timeout
                result = await asyncio.wait_for(
                    self.execute_tool(name, arguments),
                    timeout=30.0  # 30 second timeout
                )
                
                return result
                
            except asyncio.TimeoutError:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: Tool execution timed out")],
                    isError=True
                )
            except Exception as e:
                logger.error(f"Tool execution error: {e}", exc_info=True)
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute tool with business logic."""
        # Tool implementation with proper error handling
        if name == "example_tool":
            try:
                # Validate arguments
                required_args = ["input_param"]
                for arg in required_args:
                    if arg not in arguments:
                        raise ValueError(f"Missing required argument: {arg}")
                
                # Execute tool logic
                result = self.process_tool_logic(arguments)
                
                return CallToolResult(
                    content=[TextContent(type="text", text=result)],
                    isError=False
                )
            except ValueError as e:
                # Handle validation errors
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Validation error: {str(e)}")],
                    isError=True
                )
            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error in tool {name}: {e}", exc_info=True)
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Internal error: {str(e)}")],
                    isError=True
                )
        
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True
        )
```

### 6. Configuration and Initialization Patterns

```python
import argparse
from dataclasses import dataclass
from typing import Optional

@dataclass
class ServerConfig:
    """Server configuration following official patterns."""
    name: str = "mcp-server"
    transport: str = "stdio"
    host: str = "0.0.0.0"
    port: int = 3020
    log_level: str = "INFO"
    max_connections: int = 100
    timeout: float = 30.0
    
    @classmethod
    def from_args(cls) -> 'ServerConfig':
        """Create config from command line arguments."""
        parser = argparse.ArgumentParser(description="MCP Server")
        
        parser.add_argument(
            "--transport",
            choices=["stdio", "http", "sse", "websocket"],
            default="stdio",
            help="Transport type"
        )
        
        parser.add_argument(
            "--host",
            default="0.0.0.0",
            help="Host for HTTP transport"
        )
        
        parser.add_argument(
            "--port",
            type=int,
            default=3020,
            help="Port for HTTP transport"
        )
        
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Logging level"
        )
        
        parser.add_argument(
            "--max-connections",
            type=int,
            default=100,
            help="Maximum concurrent connections"
        )
        
        parser.add_argument(
            "--timeout",
            type=float,
            default=30.0,
            help="Request timeout in seconds"
        )
        
        args = parser.parse_args()
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, args.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        return cls(
            transport=args.transport,
            host=args.host,
            port=args.port,
            log_level=args.log_level,
            max_connections=args.max_connections,
            timeout=args.timeout
        )

async def main():
    """Main entry point following official patterns."""
    config = ServerConfig.from_args()
    
    # Create server instance
    server = RobustMCPServer(config.name)
    
    try:
        if config.transport == "stdio":
            await run_stdio_server(server)
        elif config.transport == "http":
            await run_http_server(server, config.host, config.port)
        elif config.transport == "sse":
            await run_advanced_http_server(server, config.host, config.port)
        else:
            logger.error(f"Unsupported transport: {config.transport}")
            return 1
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Server failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
```

## Transport-Specific Implementation Details

### STDIO Transport Best Practices

```python
# Official STDIO pattern with proper error handling
async def run_stdio_server(server: MCPServer) -> None:
    """Run MCP server with STDIO transport."""
    logger.info("Starting MCP Server with STDIO transport...")
    
    try:
        # Use context manager for proper cleanup
        async with stdio_server() as (read_stream, write_stream):
            # Run server with initialization options
            await server.server.run(
                read_stream,
                write_stream,
                server.server.create_initialization_options()
            )
    except BrokenPipeError:
        logger.info("STDIO connection closed")
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    except Exception as e:
        logger.error(f"STDIO server error: {e}")
        raise
```

### HTTP/SSE Transport Best Practices

```python
# Proper SSE implementation with keepalive
async def run_sse_server(server: MCPServer, host: str, port: int) -> None:
    """Run MCP server with SSE transport."""
    app = web.Application()
    
    # SSE handler with proper event formatting
    async def sse_handler(request):
        response = web.StreamResponse()
        response.headers.update({
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        })
        await response.prepare(request)
        
        # Send initial connection event
        await response.write(b'event: connected\ndata: {"status": "ready"}\n\n')
        
        try:
            # Create SSE transport
            transport = SseServerTransport(f"http://{host}:{port}/mcp")
            
            # Handle MCP session
            async def handle_session(streams):
                read_stream, write_stream = streams
                await server.server.run(
                    read_stream,
                    write_stream,
                    server.server.create_initialization_options()
                )
            
            # Process SSE events
            async for event in transport.events():
                await response.write(f'event: mcp\ndata: {json.dumps(event)}\n\n'.encode())
                
                # Send keepalive every 30 seconds
                await response.write(b'event: keepalive\ndata: {"timestamp": "' + 
                                   str(asyncio.get_event_loop().time()).encode() + b'"}\n\n')
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info("SSE connection cancelled")
        except Exception as e:
            logger.error(f"SSE handler error: {e}")
            await response.write(f'event: error\ndata: {json.dumps({"error": str(e)})}\n\n'.encode())
        finally:
            await response.write(b'event: disconnected\ndata: {"status": "closed"}\n\n')
        
        return response
    
    app.router.add_get('/mcp', sse_handler)
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"SSE server started on {host}:{port}")
    
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
```

## Error Handling and Logging Patterns

```python
# Comprehensive logging configuration
def setup_logging(level: str = "INFO") -> None:
    """Setup comprehensive logging for MCP server."""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('mcp-server.log'),
            logging.handlers.RotatingFileHandler(
                'mcp-server.log',
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # Configure specific loggers
    logging.getLogger('mcp').setLevel(logging.DEBUG)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

# Structured error logging
def log_mcp_error(error: Exception, context: Dict[str, Any]) -> None:
    """Log MCP errors with structured context."""
    logger.error(
        "MCP Error",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "traceback": traceback.format_exc()
        }
    )
```

## Testing Patterns

```python
import pytest
from unittest.mock import Mock, AsyncMock

# Unit test pattern for MCP tools
@pytest.mark.asyncio
async def test_tool_execution():
    """Test MCP tool execution."""
    server = RobustMCPServer("test-server")
    
    # Test successful execution
    result = await server.execute_tool("example_tool", {"input_param": "test"})
    assert not result.isError
    assert "test" in result.content[0].text
    
    # Test error handling
    result = await server.execute_tool("example_tool", {})
    assert result.isError
    assert "required argument" in result.content[0].text
    
    # Test unknown tool
    result = await server.execute_tool("unknown_tool", {})
    assert result.isError
    assert "Unknown tool" in result.content[0].text

# Integration test pattern
@pytest.mark.asyncio
async def test_stdio_transport():
    """Test STDIO transport."""
    server = RobustMCPServer("test-server")
    
    # Mock stdio streams
    read_stream = AsyncMock()
    write_stream = AsyncMock()
    
    # Test server initialization
    init_options = server.server.create_initialization_options()
    assert init_options is not None
    
    # Test tool listing
    tools_result = await server.server.list_tools()
    assert isinstance(tools_result, ListToolsResult)
```

## Deployment Patterns

### Docker Implementation

```dockerfile
# Official MCP server Dockerfile pattern
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 mcp-user && chown -R mcp-user:mcp-user /app
USER mcp-user

# Health check with proper endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3020/health || exit 1

# Expose port
EXPOSE 3020

# Run with proper transport
CMD ["python", "mcp_server.py", "--transport", "http", "--host", "0.0.0.0", "--port", "3020"]
```

### Docker Compose Pattern

```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    ports:
      - "3020:3020"
    environment:
      - LOG_LEVEL=INFO
      - MAX_CONNECTIONS=100
      - TIMEOUT=30.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3020/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

## Best Practices Summary

1. **Follow Official API Patterns**: Use the exact method signatures and parameter orders from the MCP specification
2. **Implement Proper Error Handling**: Always return CallToolResult with appropriate error flags
3. **Use Context Managers**: Ensure proper resource cleanup with async context managers
4. **Configure CORS Properly**: For browser-based clients, implement proper CORS headers
5. **Implement Health Checks**: Always provide health check endpoints for monitoring
6. **Use Structured Logging**: Implement comprehensive logging for debugging and monitoring
7. **Handle Timeouts**: Implement request timeouts to prevent hanging operations
8. **Validate Inputs**: Always validate tool arguments before processing
9. **Test Thoroughly**: Write unit and integration tests for all components
10. **Document APIs**: Provide clear documentation for available tools and their usage

These patterns ensure your MCP server implementation is robust, maintainable, and compliant with the official MCP specification.