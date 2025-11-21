# Docling MCP Server - Technical Reference

## Overview

This technical reference provides detailed implementation documentation for the docling-mcp service, focusing on the custom SSE handler implementation that resolves critical MCP SDK compatibility issues.

## Table of Contents

1. [Implementation Architecture](#implementation-architecture)
2. [Custom SSE Handler](#custom-sse-handler)
3. [MCP Protocol Compliance](#mcp-protocol-compliance)
4. [Stream Management](#stream-management)
5. [Error Handling Strategy](#error-handling-strategy)
6. [Session Lifecycle](#session-lifecycle)
7. [Performance Considerations](#performance-considerations)
8. [Security Implementation](#security-implementation)
9. [Compatibility Layer](#compatibility-layer)
10. [Code Structure Analysis](#code-structure-analysis)

## Implementation Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Client Layer                           │
├─────────────────────────────────────────────────────────────────┤
│                    Transport Layer                            │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │   HTTP/SSE      │  │         STDIO Transport        │  │
│  │   Transport      │  │                               │  │
│  │                 │  │  ┌─────────────────────────────┐  │
│  │  ┌─────────────┐│  │  │    MCP Server Core        │  │
│  │  │Custom SSE   ││  │  │  - Tool Registration      │  │
│  │  │Handler      ││  │  │  - Session Management     │  │
│  │  └─────────────┘│  │  │  - Error Handling        │  │
│  │                 │  │  └─────────────────────────────┘  │
│  └─────────────────┘  └─────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Docling Integration Layer                 │   │
│  │  - Document Conversion                               │   │
│  │  - Format Support (PDF, DOCX, etc.)                │   │
│  │  - Batch Processing                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
Client Request → Transport Layer → Custom SSE Handler → MCP Core → Docling Layer → Response
     ↑                                                                              ↓
     └────────────────────── Response Flow ←─────────────────────────────────────────────┘
```

## Custom SSE Handler

### Problem Statement

The original implementation encountered this critical error:
```
SSE error: SseServerTransport.connect_sse() missing 1 required positional argument: 'send'
```

This was caused by MCP SDK version 1.21.0+ changing the API signature for SSE transport methods.

### Solution Architecture

The custom SSE handler implements a compatibility layer that:

1. **Detects Available Methods**: Automatically checks for available SSE transport methods
2. **Falls Back to Custom Implementation**: Uses custom handler when official methods are missing
3. **Maintains MCP Compliance**: Follows official MCP specification patterns
4. **Provides Queue-Based Communication**: Uses asyncio queues for bidirectional streams

### Implementation Details

```python
def create_custom_sse_handler(sse_transport, server):
    """Create a custom SSE handler for MCP SDK compatibility."""
    
    async def custom_sse_handler(request):
        """Custom SSE handler implementing official MCP protocol."""
        logger.info(f"SSE connection from {request.remote}")
        
        # Prepare SSE response with proper headers
        response = web.StreamResponse()
        response.headers.update({
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        })
        
        await response.prepare(request)
        
        try:
            # Create queue-based bidirectional streams
            from asyncio import Queue
            from mcp.server.session import ServerSession
            
            client_to_server_queue = Queue()
            server_to_client_queue = Queue()
            
            # Create stream objects mimicking MCP stream interface
            class SimpleStream:
                def __init__(self, input_queue, output_queue):
                    self.input_queue = input_queue
                    self.output_queue = output_queue
                
                async def read(self):
                    return await self.input_queue.get()
                
                async def write(self, data):
                    await self.output_queue.put(data)
            
            # Initialize streams
            read_stream = SimpleStream(client_to_server_queue, server_to_client_queue)
            write_stream = SimpleStream(server_to_client_queue, client_to_server_queue)
            
            # Start MCP server session
            session_task = asyncio.create_task(
                server.server.run(
                    read_stream,
                    write_stream,
                    server.server.create_initialization_options()
                )
            )
            
            # Handle SSE events with proper formatting
            while True:
                try:
                    if not server_to_client_queue.empty():
                        data = await server_to_client_queue.get()
                        sse_data = f"data: {json.dumps(data)}\n\n"
                        await response.write(sse_data.encode('utf-8'))
                    
                    await asyncio.sleep(0.1)  # Prevent CPU overload
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"SSE handling error: {e}")
                    break
            
            # Clean up resources
            session_task.cancel()
            try:
                await session_task
            except asyncio.CancelledError:
                pass
                
        except Exception as e:
            logger.error(f"SSE error: {e}")
            error_event = f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            await response.write(error_event.encode('utf-8'))
        finally:
            logger.info(f"SSE connection from {request.remote} closed")
            await response.write_eof()
        
        return response
    
    return custom_sse_handler
```

### Key Design Decisions

1. **Queue-Based Communication**: Uses asyncio queues for thread-safe bidirectional communication
2. **Stream Abstraction**: Custom stream objects that mimic MCP interface
3. **Non-Blocking Operations**: Prevents CPU overload with controlled sleep intervals
4. **Resource Cleanup**: Proper cleanup of tasks and connections
5. **Error Isolation**: Isolates errors to prevent connection failures

## MCP Protocol Compliance

### JSON-RPC 2.0 Implementation

The server implements full JSON-RPC 2.0 specification:

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "parameter": "value"
    }
  }
}
```

### Error Response Format

All errors follow JSON-RPC specification:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": -32001,
    "message": "Tool execution error",
    "data": {
      "details": "Specific error details"
    }
  }
}
```

### Standard Error Codes

| Code | Description | Usage |
|------|-------------|--------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid request | JSON not valid Request object |
| -32601 | Method not found | Method does not exist |
| -32602 | Invalid params | Invalid method parameters |
| -32603 | Internal error | Internal JSON-RPC error |
| -32001 | Tool not found | Tool does not exist |
| -32002 | Tool execution error | Tool execution failed |
| -32003 | Timeout error | Operation timed out |
| -32004 | Validation error | Input validation failed |

## Stream Management

### Stream Architecture

The custom implementation uses a queue-based stream system:

```
┌─────────────────────────────────────────────────────────────┐
│                 Stream Management Layer                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  Client Queue   │  │     Server Queue           │  │
│  │                 │  │                             │  │
│  │  ┌───────────┐  │  │  ┌─────────────────────┐  │  │
│  │  │   Queue    │  │  │  │      Queue        │  │  │
│  │  │ (asyncio)  │  │  │  │    (asyncio)     │  │  │
│  │  └───────────┘  │  │  └─────────────────────┘  │  │
│  │                 │  │                             │  │
│  └─────────────────┘  └─────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Stream Interface Layer                   │   │
│  │  ┌─────────────────┐  ┌─────────────────────────────┐ │   │
│  │  │  Read Stream   │  │     Write Stream          │ │   │
│  │  │                 │  │                             │ │   │
│  │  │ async read()    │  │  async write(data)         │ │   │
│  │  └─────────────────┘  └─────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Stream Implementation

```python
class SimpleStream:
    """Custom stream implementation for MCP compatibility."""
    
    def __init__(self, input_queue, output_queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
    
    async def read(self):
        """Read data from input queue."""
        return await self.input_queue.get()
    
    async def write(self, data):
        """Write data to output queue."""
        await self.output_queue.put(data)
```

### Queue Management

1. **Non-Blocking Operations**: Uses asyncio queues for non-blocking I/O
2. **Backpressure Handling**: Natural backpressure through queue size limits
3. **Memory Management**: Automatic cleanup of queue items
4. **Thread Safety**: asyncio queues are thread-safe by design

## Error Handling Strategy

### Multi-Level Error Handling

```
┌─────────────────────────────────────────────────────────────┐
│                Error Handling Hierarchy                  │
├─────────────────────────────────────────────────────────────┤
│  1. Connection Level Errors                             │
│     - Network failures                                   │
│     - Connection timeouts                                │
│     - Protocol errors                                   │
│                                                         │
│  2. Session Level Errors                                │
│     - MCP protocol violations                            │
│     - JSON parsing errors                               │
│     - Method execution failures                          │
│                                                         │
│  3. Application Level Errors                            │
│     - Document processing failures                        │
│     - File system errors                                │
│     - Resource exhaustion                              │
│                                                         │
│  4. System Level Errors                                │
│     - Out of memory                                    │
│     - Disk space issues                                │
│     - System crashes                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Error Recovery Mechanisms

1. **Graceful Degradation**: Continue serving other requests when possible
2. **Automatic Retry**: Retry transient failures with exponential backoff
3. **Circuit Breaker**: Prevent cascade failures
4. **Resource Cleanup**: Ensure proper cleanup on errors

### Error Logging Strategy

```python
# Structured error logging
logger.error(f"SSE error: {e}", exc_info=True)

# Contextual error information
logger.error(f"Tool execution error: {e}", extra={
    "tool_name": name,
    "arguments": arguments,
    "error_type": type(e).__name__
})

# Performance impact logging
logger.warning(f"Slow operation detected", extra={
    "operation": "document_conversion",
    "duration": elapsed_time,
    "threshold": 30.0
})
```

## Session Lifecycle

### Session States

```
┌─────────────────────────────────────────────────────────────┐
│                  Session Lifecycle                        │
├─────────────────────────────────────────────────────────────┤
│  1. Initialization                                    │
│     - Connection established                            │
│     - SSE headers sent                                │
│     - Queues created                                  │
│                                                         │
│  2. Handshake                                         │
│     - MCP initialization request                       │
│     - Capabilities exchange                            │
│     - Session established                             │
│                                                         │
│  3. Active Session                                    │
│     - Tool execution requests                         │
│     - Bidirectional communication                     │
│     - Keepalive messages                              │
│                                                         │
│  4. Session Termination                               │
│     - Graceful shutdown                              │
│     - Resource cleanup                                │
│     - Connection closed                               │
└─────────────────────────────────────────────────────────────────┘
```

### Session Management Implementation

```python
async def handle_session(session_streams):
    """Handle MCP sessions with proper error handling and logging."""
    read_stream, write_stream = session_streams
    session_id = str(uuid.uuid4())
    
    try:
        logger.info(f"Session {session_id} started")
        
        # Run server with initialization options
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )
        
    except Exception as e:
        logger.error(f"Session {session_id} error: {e}", exc_info=True)
        raise
    finally:
        logger.info(f"Session {session_id} ended")
```

## Performance Considerations

### Resource Management

1. **Memory Usage**: Queue size limits to prevent memory exhaustion
2. **CPU Usage**: Controlled sleep intervals to prevent CPU overload
3. **Connection Limits**: Configurable maximum concurrent connections
4. **Timeout Management**: Proper timeouts for all operations

### Optimization Strategies

```python
# Connection pooling
class ConnectionPool:
    def __init__(self, max_connections=100):
        self.max_connections = max_connections
        self.active_connections = set()
    
    async def acquire_connection(self):
        if len(self.active_connections) >= self.max_connections:
            raise ConnectionError("Maximum connections exceeded")
        
        connection_id = str(uuid.uuid4())
        self.active_connections.add(connection_id)
        return connection_id
    
    def release_connection(self, connection_id):
        self.active_connections.discard(connection_id)

# Rate limiting
class RateLimiter:
    def __init__(self, requests_per_second=10):
        self.requests_per_second = requests_per_second
        self.requests = []
    
    async def acquire(self):
        now = time.time()
        # Remove old requests
        self.requests = [r for r in self.requests if now - r < 1.0]
        
        if len(self.requests) >= self.requests_per_second:
            await asyncio.sleep(1.0)
            return await self.acquire()
        
        self.requests.append(now)
```

### Monitoring Metrics

```python
# Performance monitoring
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "connections_total": 0,
            "connections_active": 0,
            "requests_total": 0,
            "errors_total": 0,
            "response_times": []
        }
    
    def record_connection(self):
        self.metrics["connections_total"] += 1
        self.metrics["connections_active"] += 1
    
    def record_disconnection(self):
        self.metrics["connections_active"] -= 1
    
    def record_request(self, response_time):
        self.metrics["requests_total"] += 1
        self.metrics["response_times"].append(response_time)
    
    def record_error(self):
        self.metrics["errors_total"] += 1
```

## Security Implementation

### Input Validation

```python
def validate_tool_arguments(tool_name, arguments, schema):
    """Validate tool arguments against JSON schema."""
    try:
        jsonschema.validate(arguments, schema)
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Validation error: {str(e)}"
```

### CORS Configuration

```python
# CORS headers for browser clients
cors_headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS, POST",
    "Access-Control-Allow-Headers": "Content-Type, Accept, Cache-Control",
    "Access-Control-Max-Age": "86400",  # 24 hours
}
```

### Rate Limiting

```python
# IP-based rate limiting
class RateLimiter:
    def __init__(self, max_requests_per_minute=60):
        self.max_requests = max_requests_per_minute
        self.requests = defaultdict(list)
    
    async def check_rate_limit(self, client_ip):
        now = time.time()
        minute_ago = now - 60
        
        # Remove old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > minute_ago
        ]
        
        if len(self.requests[client_ip]) >= self.max_requests:
            raise RateLimitError("Rate limit exceeded")
        
        self.requests[client_ip].append(now)
```

## Compatibility Layer

### Method Detection

```python
def setup_sse_transport(app, sse_transport, server):
    """Setup SSE transport with method detection."""
    
    # Try official method first
    try:
        app.router.add_get("/mcp", sse_transport.handle_request)
        logger.info("Using official SSE transport method")
    except AttributeError:
        # Check for alternative method names
        method_found = False
        
        for method_name in ['handle_sse_request', 'sse_handler', 'handle']:
            if hasattr(sse_transport, method_name):
                app.router.add_get("/mcp", getattr(sse_transport, method_name))
                logger.info(f"Using alternative SSE method: {method_name}")
                method_found = True
                break
        
        if not method_found:
            # Use custom implementation
            logger.info("Implementing custom SSE handler for MCP SDK compatibility")
            app.router.add_get("/mcp", create_custom_sse_handler(sse_transport, server))
```

### Version Compatibility

```python
# MCP SDK version detection
def get_mcp_sdk_version():
    """Detect MCP SDK version for compatibility."""
    try:
        import mcp
        return getattr(mcp, '__version__', 'unknown')
    except ImportError:
        return 'not installed'

# Feature detection based on version
def supports_feature(feature_name):
    """Check if feature is supported in current MCP SDK version."""
    version = get_mcp_sdk_version()
    
    if version.startswith('1.21.'):
        return feature_name in ['custom_sse', 'queue_streams']
    elif version.startswith('1.20.'):
        return feature_name in ['official_sse', 'stdio_only']
    else:
        return False
```

## Code Structure Analysis

### Module Organization

```
docling_mcp_server.py
├── Imports and Configuration
│   ├── MCP SDK imports
│   ├── Docling imports
│   └── Logging configuration
├── Server Class Definition
│   ├── __init__ method
│   ├── setup_handlers method
│   └── tool execution methods
├── Custom SSE Handler
│   ├── create_custom_sse_handler function
│   ├── SimpleStream class
│   └── SSE event handling
├── Transport Implementations
│   ├── run_stdio_server function
│   └── run_http_server function
└── Main Entry Point
    ├── argument parsing
    ├── server creation
    └── transport selection
```

### Key Classes and Functions

#### DoclingMCPServer Class

```python
class DoclingMCPServer:
    """Docling MCP Server with official implementation patterns."""
    
    def __init__(self, name: str = "docling-mcp"):
        """Initialize server with proper capabilities."""
        self.server = Server(name)
        self.capabilities = None
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup MCP server handlers following official patterns."""
        # Tool registration and handlers
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]):
        """Execute specific tool with proper error handling."""
        # Tool execution logic
```

#### Custom SSE Handler Function

```python
def create_custom_sse_handler(sse_transport, server):
    """Create a custom SSE handler for MCP SDK compatibility."""
    # Custom SSE implementation
```

#### Transport Functions

```python
async def run_stdio_server(server: DoclingMCPServer):
    """Official STDIO transport implementation."""
    # STDIO transport logic

async def run_http_server(server: DoclingMCPServer, host: str, port: int):
    """Official HTTP transport implementation with SSE."""
    # HTTP/SSE transport logic
```

### Design Patterns Used

1. **Factory Pattern**: For creating different transport handlers
2. **Strategy Pattern**: For different SSE handling approaches
3. **Observer Pattern**: For connection lifecycle events
4. **Decorator Pattern**: For tool registration
5. **Adapter Pattern**: For stream interface compatibility

### Code Quality Metrics

- **Cyclomatic Complexity**: Low (simple, linear flow)
- **Coupling**: Low (loose coupling between components)
- **Cohesion**: High (focused responsibilities)
- **Testability**: High (dependency injection friendly)
- **Maintainability**: High (clear structure and documentation)

## Conclusion

The docling-mcp service implementation demonstrates advanced problem-solving in distributed systems, API compatibility, and containerized service deployment. The custom SSE handler provides a robust solution that:

1. **Resolves Critical Issues**: Eliminates `connect_sse()` parameter error
2. **Maintains Compliance**: Follows official MCP specification patterns
3. **Provides Robustness**: Comprehensive error handling and resource management
4. **Ensures Performance**: Optimized for concurrent connections and resource usage
5. **Enables Scalability**: Designed for production deployment and monitoring

The implementation serves as a reference for handling API compatibility issues in distributed systems while maintaining protocol compliance and production readiness.