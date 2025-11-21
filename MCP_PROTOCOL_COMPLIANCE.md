# MCP Protocol Compliance Requirements

## Overview

This document outlines the official MCP (Model Context Protocol) compliance requirements based on the MCP 1.0+ specification. It provides detailed implementation guidelines for HTTP transport, streaming support, and client capability requirements.

## Official MCP Specification Reference

- **MCP Specification**: https://modelcontextprotocol.io/specification
- **Transport Specification**: https://modelcontextprotocol.io/specification/transports
- **Protocol Messages**: https://modelcontextprotocol.io/specification/messages
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk

## Core Protocol Requirements

### 1. Message Format Compliance

#### JSON-RPC 2.0 Compliance
All MCP messages must follow JSON-RPC 2.0 specification:

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "method_name",
  "params": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**Required Implementation:**
```python
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class JsonRpcRequest:
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: Optional[Dict[str, Any]] = None

@dataclass
class JsonRpcResponse:
    jsonrpc: str = "2.0"
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

@dataclass
class JsonRpcError:
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None
```

#### MCP-Specific Message Types

**Initialize Request (Required):**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "initialize",
  "params": {
    "protocolVersion": "1.0",
    "capabilities": {
      "tools": {
        "listChanged": true
      }
    },
    "clientInfo": {
      "name": "client-name",
      "version": "1.0.0"
    }
  }
}
```

**Initialize Response (Required):**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "protocolVersion": "1.0",
    "capabilities": {
      "tools": {
        "listChanged": true
      }
    },
    "serverInfo": {
      "name": "server-name",
      "version": "1.0.0"
    }
  }
}
```

**Implementation Requirements:**
```python
from mcp.types import InitializeRequest, InitializeResult, ServerCapabilities

class MCPServer:
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.capabilities = ServerCapabilities(
            tools=ToolsCapability(listChanged=True)
        )
    
    async def handle_initialize(self, request: InitializeRequest) -> InitializeResult:
        """Handle initialize request per MCP specification."""
        # Validate protocol version
        if request.params.protocolVersion != "1.0":
            raise ValueError("Unsupported protocol version")
        
        # Return server capabilities
        return InitializeResult(
            protocolVersion="1.0",
            capabilities=self.capabilities,
            serverInfo=Implementation(name=self.name, version=self.version)
        )
```

### 2. Transport Protocol Requirements

#### STDIO Transport

**Message Framing:**
- Messages must be separated by newlines (`\n`)
- Each message must be a complete JSON-RPC object
- UTF-8 encoding is required

**Implementation Pattern:**
```python
import json
import asyncio

class StdioTransport:
    def __init__(self):
        self.read_stream = None
        self.write_stream = None
    
    async def start(self):
        """Start STDIO transport with proper framing."""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            self.read_stream = read_stream
            self.write_stream = write_stream
            
            async for message in read_stream:
                # Parse JSON-RPC message
                try:
                    request = json.loads(message)
                    response = await self.handle_request(request)
                    
                    # Send response with proper framing
                    await write_stream.send(json.dumps(response) + '\n')
                except json.JSONDecodeError:
                    error_response = self.create_error_response(
                        -32700, "Parse error", {"message": "Invalid JSON"}
                    )
                    await write_stream.send(json.dumps(error_response) + '\n')
```

#### HTTP Transport with Server-Sent Events (SSE)

**SSE Protocol Requirements:**

1. **Content-Type Header**: Must be `text/event-stream`
2. **Event Format**: Must follow SSE specification
3. **Connection Handling**: Must support reconnection
4. **CORS Support**: Required for browser clients

**SSE Message Format:**
```
event: message
data: {"jsonrpc": "2.0", "id": "1", "result": {...}}

event: error
data: {"jsonrpc": "2.0", "id": "1", "error": {"code": -32600, "message": "Invalid request"}}

event: keepalive
data: {"type": "keepalive", "timestamp": 1234567890}
```

**Implementation Pattern:**
```python
from aiohttp import web
import json
import asyncio

class SseTransport:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.active_connections = set()
    
    async def handle_request(self, request):
        """Handle SSE request per MCP specification."""
        response = web.StreamResponse()
        response.headers.update({
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Accept',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
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

#### WebSocket Transport (Optional)

**WebSocket Protocol Requirements:**
```python
class WebSocketTransport:
    async def handle_websocket(self, request):
        """Handle WebSocket connections per MCP specification."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    # Parse JSON-RPC message
                    try:
                        request_data = json.loads(msg.data)
                        response = await self.handle_request(request_data)
                        await ws.send_str(json.dumps(response))
                    except json.JSONDecodeError:
                        error_response = self.create_error_response(
                            -32700, "Parse error"
                        )
                        await ws.send_str(json.dumps(error_response))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
        finally:
            await ws.close()
        
        return ws
```

### 3. Tool Protocol Requirements

#### Tool Definition Schema

**Required Tool Schema:**
```python
from mcp.types import Tool, ToolInputSchema

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
```

#### Tool Execution Requirements

**CallToolRequest Handling:**
```python
from mcp.types import CallToolRequest, CallToolResult, TextContent, ImageContent

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

**Result Content Types:**
```python
# Text content (most common)
text_result = CallToolResult(
    content=[TextContent(type="text", text="Tool execution result")],
    isError=False
)

# Multiple content types
mixed_result = CallToolResult(
    content=[
        TextContent(type="text", text="Processing complete"),
        TextContent(type="text", text="Additional details here")
    ],
    isError=False
)

# Error result
error_result = CallToolResult(
    content=[TextContent(type="text", text="Error: Invalid input")],
    isError=True
)
```

### 4. Error Handling Requirements

#### JSON-RPC Error Codes

**Standard Error Codes:**
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

#### Error Response Format

**Required Error Format:**
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

# Usage examples
parse_error = self.create_error_response("1", -32700, "Parse error", {"details": "Invalid JSON"})
method_not_found = self.create_error_response("2", -32601, "Method not found", {"method": "unknown_method"})
```

### 5. Client Capability Requirements

#### Server Capability Advertisement

**Required Capabilities:**
```python
from mcp.types import ServerCapabilities, ToolsCapability, LoggingCapability

class MCPServer:
    def __init__(self):
        self.capabilities = ServerCapabilities(
            tools=ToolsCapability(
                listChanged=True  # Server supports dynamic tool list changes
            ),
            logging=LoggingCapability(
                level=True  # Server supports log level configuration
            )
        )
    
    def get_server_capabilities(self) -> dict:
        """Return server capabilities per MCP specification."""
        return {
            "tools": {
                "listChanged": self.capabilities.tools.listChanged
            },
            "logging": {
                "level": self.capabilities.logging.level
            }
        }
```

#### Client Capability Handling

**Client Capability Processing:**
```python
async def handle_initialize(self, request: InitializeRequest) -> InitializeResult:
    """Process client capabilities and negotiate features."""
    client_capabilities = request.params.capabilities
    
    # Process client tool capabilities
    if hasattr(client_capabilities, 'tools'):
        client_tools = client_capabilities.tools
        logger.info(f"Client tool capabilities: listChanged={getattr(client_tools, 'listChanged', False)}")
    
    # Process client logging capabilities
    if hasattr(client_capabilities, 'logging'):
        client_logging = client_capabilities.logging
        logger.info(f"Client logging capabilities: level={getattr(client_logging, 'level', False)}")
    
    # Return negotiated capabilities
    return InitializeResult(
        protocolVersion="1.0",
        capabilities=self.capabilities,
        serverInfo=Implementation(name=self.name, version=self.version)
    )
```

### 6. Streaming and Real-time Requirements

#### Server-Sent Events Streaming

**Event Stream Format:**
```python
class McpEventStream:
    """Handle MCP event streaming per SSE specification."""
    
    async def send_tool_list_changed(self, response_stream):
        """Send tool list changed event."""
        event_data = {
            "jsonrpc": "2.0",
            "method": "notifications/tools/list_changed",
            "params": {}
        }
        await self.send_event(response_stream, 'tools_list_changed', event_data)
    
    async def send_progress_update(self, response_stream, progress: float, message: str):
        """Send progress update during long operations."""
        event_data = {
            "jsonrpc": "2.0",
            "method": "notifications/progress",
            "params": {
                "progress": progress,
                "message": message
            }
        }
        await self.send_event(response_stream, 'progress', event_data)
```

#### Connection Lifecycle Management

**Connection State Handling:**
```python
class ConnectionManager:
    """Manage MCP connection lifecycle."""
    
    def __init__(self):
        self.active_connections = {}
        self.connection_timeouts = {}
    
    async def handle_connection(self, connection_id: str, response_stream):
        """Handle new MCP connection."""
        self.active_connections[connection_id] = {
            'stream': response_stream,
            'created_at': asyncio.get_event_loop().time(),
            'last_activity': asyncio.get_event_loop().time()
        }
        
        try:
            # Send initial connection event
            await self.send_event(response_stream, 'connected', {
                'connection_id': connection_id,
                'server_info': self.get_server_info()
            })
            
            # Start activity monitoring
            await self.monitor_connection_activity(connection_id)
            
        except Exception as e:
            logger.error(f"Connection {connection_id} error: {e}")
        finally:
            await self.cleanup_connection(connection_id)
    
    async def monitor_connection_activity(self, connection_id: str):
        """Monitor connection for activity and timeouts."""
        while connection_id in self.active_connections:
            conn_info = self.active_connections[connection_id]
            
            # Check for timeout (5 minutes of inactivity)
            current_time = asyncio.get_event_loop().time()
            if current_time - conn_info['last_activity'] > 300:  # 5 minutes
                logger.warning(f"Connection {connection_id} timed out")
                break
            
            await asyncio.sleep(30)  # Check every 30 seconds
```

### 7. Security and Validation Requirements

#### Input Validation

**Schema Validation:**
```python
from jsonschema import validate, ValidationError

class InputValidator:
    """Validate MCP requests against schemas."""
    
    def validate_tool_arguments(self, arguments: dict, schema: dict) -> list:
        """Validate tool arguments against JSON Schema."""
        errors = []
        
        try:
            validate(instance=arguments, schema=schema)
        except ValidationError as e:
            errors.append(f"Validation error: {e.message}")
        
        # Additional MCP-specific validations
        if 'file_path' in arguments:
            if not self.is_safe_file_path(arguments['file_path']):
                errors.append("Unsafe file path provided")
        
        if 'url' in arguments:
            if not self.is_safe_url(arguments['url']):
                errors.append("Unsafe URL provided")
        
        return errors
    
    def is_safe_file_path(self, file_path: str) -> bool:
        """Check if file path is safe (no directory traversal)."""
        # Prevent directory traversal
        if '..' in file_path or file_path.startswith('/'):
            return False
        
        # Additional safety checks
        try:
            Path(file_path).resolve()
            return True
        except Exception:
            return False
    
    def is_safe_url(self, url: str) -> bool:
        """Check if URL is safe (no file:// or dangerous schemes)."""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        allowed_schemes = ['http', 'https']
        
        return parsed.scheme in allowed_schemes
```

#### Transport Security

**HTTP Security Headers:**
```python
def get_security_headers(self) -> dict:
    """Get security headers for HTTP transport."""
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'",
    }
```

### 8. Performance and Resource Requirements

#### Memory Management

**Resource Cleanup:**
```python
class ResourceManager:
    """Manage server resources and cleanup."""
    
    def __init__(self):
        self.active_resources = {}
        self.cleanup_tasks = []
    
    async def cleanup_resources(self):
        """Cleanup all active resources."""
        for resource_id, resource in self.active_resources.items():
            try:
                if hasattr(resource, 'cleanup'):
                    await resource.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up resource {resource_id}: {e}")
        
        self.active_resources.clear()
    
    def register_cleanup_task(self, task: asyncio.Task):
        """Register a cleanup task to run on shutdown."""
        self.cleanup_tasks.append(task)
```

#### Request Timeout Handling

**Timeout Implementation:**
```python
async def execute_with_timeout(self, coro, timeout: float = 30.0):
    """Execute coroutine with timeout per MCP specification."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Operation timed out after {timeout} seconds")
        raise
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
```

## Compliance Testing

### Protocol Compliance Test Suite

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
    
    @pytest.mark.asyncio
    async def test_tool_execution_compliance(self):
        """Test tool execution compliance."""
        server = MCPServer("test-server", "1.0.0")
        
        # Test valid tool call
        request = CallToolRequest(
            id="test-2",
            params={
                "name": "example_tool",
                "arguments": {"required_param": "test_value"}
            }
        )
        
        result = await server.handle_call_tool(request)
        assert isinstance(result, CallToolResult)
        assert hasattr(result, 'content')
        assert hasattr(result, 'isError')
    
    def test_error_response_compliance(self):
        """Test error response format compliance."""
        server = MCPServer("test-server", "1.0.0")
        
        error_response = server.create_error_response("test-3", -32600, "Invalid request")
        
        assert error_response["jsonrpc"] == "2.0"
        assert error_response["id"] == "test-3"
        assert error_response["error"]["code"] == -32600
        assert error_response["error"]["message"] == "Invalid request"
```

### Transport Compliance Testing

```python
@pytest.mark.asyncio
async def test_stdio_transport_compliance(aiohttp_client):
    """Test STDIO transport compliance."""
    # Test message framing
    messages = [
        '{"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {}}\n',
        '{"jsonrpc": "2.0", "id": "2", "method": "tools/list", "params": {}}\n'
    ]
    
    for message in messages:
        # Verify proper JSON-RPC format
        parsed = json.loads(message.strip())
        assert parsed["jsonrpc"] == "2.0"
        assert "id" in parsed
        assert "method" in parsed

@pytest.mark.asyncio
async def test_http_sse_compliance(aiohttp_client):
    """Test HTTP SSE transport compliance."""
    client = await aiohttp_client(create_test_app())
    
    async with client.get('/mcp') as resp:
        # Check headers
        assert resp.headers['Content-Type'] == 'text/event-stream'
        assert resp.headers['Cache-Control'] == 'no-cache'
        assert resp.headers['Connection'] == 'keep-alive'
        
        # Read first event
        line = await resp.content.readline()
        assert line.startswith(b'event:')
        
        data_line = await resp.content.readline()
        assert data_line.startswith(b'data:')
```

## Compliance Checklist

### ✅ Core Protocol Compliance
- [ ] JSON-RPC 2.0 message format implemented
- [ ] Request/response correlation via ID field
- [ ] Proper error code usage
- [ ] Message validation implemented

### ✅ Transport Compliance
- [ ] STDIO transport with proper framing
- [ ] HTTP transport with correct headers
- [ ] SSE transport with event formatting
- [ ] WebSocket transport (if implemented)

### ✅ Tool Protocol Compliance
- [ ] Tool schema validation
- [ ] Proper CallToolResult format
- [ ] Error handling with isError flag
- [ ] Content type handling

### ✅ Capability Compliance
- [ ] Server capabilities advertised
- [ ] Client capabilities processed
- [ ] Feature negotiation implemented
- [ ] Protocol version handling

### ✅ Security Compliance
- [ ] Input validation implemented
- [ ] Safe file path handling
- [ ] URL validation for requests
- [ ] Resource access controls

### ✅ Performance Compliance
- [ ] Request timeouts implemented
- [ ] Resource cleanup procedures
- [ ] Memory management
- [ ] Connection lifecycle management

## Certification Process

### Self-Certification Steps

1. **Implement Compliance Tests**: Use the provided test suite
2. **Run Protocol Validation**: Test against official MCP test vectors
3. **Transport Testing**: Verify all transport implementations
4. **Security Audit**: Conduct security review of implementation
5. **Performance Testing**: Validate performance requirements
6. **Documentation Review**: Ensure all requirements are documented

### Third-Party Certification

For production deployments, consider third-party certification:
- MCP Implementer's Workshop compliance testing
- Independent security audit
- Performance benchmarking
- Interoperability testing with other MCP implementations

## Conclusion

This compliance guide ensures MCP server implementations meet the official specification requirements. Regular updates to this document are recommended as the MCP specification evolves. Implementation teams should maintain compliance testing as part of their continuous integration process.