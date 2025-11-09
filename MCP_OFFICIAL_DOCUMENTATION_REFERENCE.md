# MCP Official Documentation Reference Guide

## Overview

This document compiles official MCP (Model Context Protocol) documentation and implementation patterns to fix remaining issues in the docling-mcp service. It focuses on HTTP transport, streaming, and proper server initialization patterns based on the official MCP specification.

## Official MCP Specification References

### Core Specification
- **MCP Specification**: https://modelcontextprotocol.io/specification
- **Transport Specification**: https://modelcontextprotocol.io/specification/transports
- **Protocol Messages**: https://modelcontextprotocol.io/specification/messages
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk

### Key Implementation Resources
- **Official MCP Documentation**: https://modelcontextprotocol.io/
- **Python SDK Examples**: https://github.com/modelcontextprotocol/python-sdk/tree/main/examples
- **Transport Implementation Guide**: https://modelcontextprotocol.io/specification/transports

## Official MCP Server Implementation Patterns

### 1. Correct HTTP Transport with SSE Implementation

Based on the official MCP Python SDK, here's the proper pattern for HTTP transport with Server-Sent Events:

```python
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.models import InitializationOptions
import asyncio
from aiohttp import web

class OfficialMCPServer:
    def __init__(self, name: str):
        self.server = Server(name)
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup MCP server handlers following official patterns."""
        
        @self.server.list_tools()
        async def list_tools():
            return ListToolsResult(tools=[...])
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            # Tool implementation
            pass

async def run_http_server(server: OfficialMCPServer, host: str = "0.0.0.0", port: int = 3020):
    """Official HTTP transport implementation with SSE."""
    logger.info(f"Starting MCP Server with HTTP transport on {host}:{port}...")
    
    # Create aiohttp application
    app = web.Application()
    
    # Create SSE transport with proper configuration
    sse_transport = SseServerTransport(f"http://{host}:{port}/mcp")
    
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

### 2. Official STDIO Transport Pattern

```python
import asyncio
from mcp.server.stdio import stdio_server

async def run_stdio_server(server: OfficialMCPServer):
    """Official STDIO transport implementation."""
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

### 3. Correct Server Initialization Pattern

```python
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability

class ProperlyInitializedMCPServer:
    def __init__(self, name: str):
        self.server = Server(name)
        self.capabilities = ServerCapabilities(
            tools=ToolsCapability(listChanged=True)
        )
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup handlers with proper error handling."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available tools - official pattern."""
            return ListToolsResult(tools=[...])
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls with comprehensive error handling."""
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
                    timeout=30.0  # 30 second timeout per specification
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
```

## Official MCP Transport Requirements

### HTTP/SSE Transport Requirements

1. **Content-Type Header**: Must be `text/event-stream`
2. **Event Format**: Must follow SSE specification
3. **Connection Handling**: Must support reconnection
4. **CORS Support**: Required for browser clients

**Proper SSE Message Format:**
```
event: message
data: {"jsonrpc": "2.0", "id": "1", "result": {...}}

event: error
data: {"jsonrpc": "2.0", "id": "1", "error": {"code": -32600, "message": "Invalid request"}}

event: keepalive
data: {"type": "keepalive", "timestamp": 1234567890}
```

### STDIO Transport Requirements

1. **Message Framing**: Messages must be separated by newlines (`\n`)
2. **JSON Format**: Each message must be a complete JSON-RPC object
3. **UTF-8 Encoding**: Required for all messages
4. **Error Handling**: Proper JSON parsing and error responses

## Official Error Handling Patterns

### JSON-RPC Error Codes
```python
class JsonRpcErrorCodes:
    # Standard JSON-RPC error codes
    PARSE_ERROR = -32700          # Invalid JSON
    INVALID_REQUEST = -32600      # JSON is not a valid Request object
    METHOD_NOT_FOUND = -32601     # Method does not exist
    INVALID_PARAMS = -32602       # Invalid method parameters
    INTERNAL_ERROR = -32603       # Internal JSON-RPC error
    
    # MCP-specific error codes
    TOOL_NOT_FOUND = -32001       # Tool does not exist
    TOOL_EXECUTION_ERROR = -32002 # Tool execution failed
    TIMEOUT_ERROR = -32003        # Operation timed out
    VALIDATION_ERROR = -32004     # Input validation failed
```

### Proper Error Response Format
```python
def create_error_response(self, request_id: str, code: int, message: str, data: dict = None) -> dict:
    """Create error response per JSON-RPC specification."""
    error_response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }
    
    if data:
        error_response["error"]["data"] = data
    
    return error_response
```

## Official Tool Implementation Pattern

```python
from mcp.types import Tool, ToolInputSchema, CallToolResult, TextContent

# Tool must have proper JSON Schema
tool = Tool(
    name="example_tool",
    description="Description of what the tool does",
    inputSchema={
        "type": "object",
        "properties": {
            "required_param": {
                "type": "string",
                "description": "Description of the parameter"
            },
            "optional_param": {
                "type": "number",
                "description": "Optional parameter",
                "default": 42
            }
        },
        "required": ["required_param"],
        "additionalProperties": False  # Strict validation
    }
)

# Proper CallToolResult handling
async def handle_call_tool(self, request: CallToolRequest) -> CallToolResult:
    """Handle tool execution per MCP specification."""
    try:
        # Validate tool name
        if not request.params.name:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: Tool name is required")],
                isError=True
            )
        
        # Get tool implementation
        tool = self.get_tool(request.params.name)
        if not tool:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {request.params.name}")],
                isError=True
            )
        
        # Validate arguments against schema
        validation_errors = self.validate_arguments(
            request.params.arguments or {},
            tool.inputSchema
        )
        if validation_errors:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Validation error: {validation_errors}")],
                isError=True
            )
        
        # Execute tool with timeout
        result = await asyncio.wait_for(
            self.execute_tool(tool, request.params.arguments or {}),
            timeout=30.0  # 30 second timeout per specification
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
```

## Official Multi-Connection Support

### Server-Sent Events for Multiple Clients
```python
class MultiConnectionMCPServer:
    def __init__(self):
        self.active_connections = set()
        self.connection_manager = ConnectionManager()
    
    async def handle_sse_request(self, request):
        """Handle SSE request with multi-connection support."""
        response = web.StreamResponse()
        response.headers.update({
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        })
        
        await response.prepare(request)
        connection_id = id(response)
        self.active_connections.add(connection_id)
        
        try:
            # Send initial connection event
            await self.send_event(response, 'connected', {'status': 'ready'})
            
            # Start keepalive task
            keepalive_task = asyncio.create_task(self.send_keepalive(response))
            
            # Handle MCP session
            await self.handle_mcp_session(response)
            
        except asyncio.CancelledError:
            logger.info(f"SSE connection {connection_id} cancelled")
        except Exception as e:
            logger.error(f"SSE error: {e}")
            await self.send_event(response, 'error', {'message': str(e)})
        finally:
            keepalive_task.cancel()
            self.active_connections.discard(connection_id)
            await self.send_event(response, 'disconnected', {'status': 'closed'})
        
        return response
    
    async def send_event(self, response, event_type: str, data: dict):
        """Send SSE event with proper formatting."""
        event_data = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        await response.write(event_data.encode('utf-8'))
    
    async def send_keepalive(self, response):
        """Send periodic keepalive messages."""
        try:
            while True:
                await asyncio.sleep(30)  # Keepalive every 30 seconds
                await self.send_event(response, 'keepalive', {
                    'type': 'keepalive',
                    'timestamp': asyncio.get_event_loop().time()
                })
        except asyncio.CancelledError:
            pass
```

## Official Configuration and Deployment Patterns

### Proper Argument Parsing
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
        
        return cls(**vars(parser.parse_args()))
```

## Official Docker Deployment Pattern

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

## Common Implementation Issues and Official Solutions

### Issue 1: Incorrect SSE Transport Initialization
**Problem**: Using wrong parameter order or missing session handler
**Official Solution**: Use proper SSE transport setup with session handler

```python
# WRONG
await server.server.run(transport, init_options)

# CORRECT
async def handle_session(session_streams):
    read_stream, write_stream = session_streams
    await server.server.run(read_stream, write_stream, init_options)

sse_transport.handle_session = handle_session
```

### Issue 2: Missing CORS Headers
**Problem**: Browser clients cannot connect due to CORS issues
**Official Solution**: Implement proper CORS headers

```python
# Add CORS handling
app.router.add_options("/mcp", lambda req: web.Response(
    headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Accept",
    }
))
```

### Issue 3: Improper Error Handling
**Problem**: Errors not following JSON-RPC specification
**Official Solution**: Use proper error codes and formats

```python
# Proper error response
error_response = {
    "jsonrpc": "2.0",
    "id": request_id,
    "error": {
        "code": -32601,  # Method not found
        "message": "Method not found",
        "data": {"method": "unknown_method"}
    }
}
```

### Issue 4: Missing Keepalive Messages
**Problem**: SSE connections timeout due to lack of keepalive
**Official Solution**: Implement periodic keepalive messages

```python
async def send_keepalive(self, response):
    """Send periodic keepalive messages."""
    try:
        while True:
            await asyncio.sleep(30)  # Keepalive every 30 seconds
            await self.send_event(response, 'keepalive', {
                'type': 'keepalive',
                'timestamp': asyncio.get_event_loop().time()
            })
    except asyncio.CancelledError:
        pass
```

## Testing and Validation

### Official Compliance Testing
```python
import pytest
from mcp.types import InitializeRequest, CallToolRequest

class TestMcpCompliance:
    """Test suite for MCP protocol compliance."""
    
    @pytest.mark.asyncio
    async def test_initialize_request_compliance(self):
        """Test initialize request handling compliance."""
        server = MCPServer("test-server", "1.0.0")
        
        # Test valid initialize request
        request = InitializeRequest(
            id="test-1",
            params={
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        )
        
        result = await server.handle_initialize(request)
        assert result.protocolVersion == "1.0"
        assert result.serverInfo.name == "test-server"
        assert result.serverInfo.version == "1.0.0"
```

## Conclusion

This reference guide provides the official MCP implementation patterns needed to fix the remaining issues in the docling-mcp service. The key areas to focus on are:

1. **Proper HTTP/SSE transport implementation** with correct session handling
2. **Official server initialization patterns** with proper error handling
3. **Multi-connection support** with keepalive messages
4. **JSON-RPC compliance** with proper error codes and message formats
5. **CORS configuration** for browser client compatibility
6. **Docker deployment** with health checks and proper configuration

By following these official patterns, the docling-mcp service will achieve full MCP specification compliance and reliable operation.