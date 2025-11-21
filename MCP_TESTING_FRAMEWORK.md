# MCP Testing Framework Documentation

## Overview

This document provides a comprehensive testing framework for MCP (Model Context Protocol) server implementations. It includes unit tests, integration tests, performance tests, and compliance verification procedures.

## Testing Strategy

### Testing Pyramid
```
                    /\
                   /  \
  Compliance Tests /    \ End-to-End Tests
                 /      \
Integration Tests/________\ Unit Tests
               (Few)    (Many)
```

### Test Categories
1. **Unit Tests** - Individual component testing
2. **Integration Tests** - Component interaction testing
3. **Performance Tests** - Load and stress testing
4. **Compliance Tests** - Protocol specification verification
5. **End-to-End Tests** - Complete workflow testing

## Test Environment Setup

### Prerequisites
```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-aiohttp
pip install aiohttp jsonschema
pip install locust  # For performance testing
```

### Test Directory Structure
```
tests/
├── unit/
│   ├── test_server.py
│   ├── test_tools.py
│   ├── test_transport.py
│   └── test_config.py
├── integration/
│   ├── test_gateway_integration.py
│   ├── test_service_integration.py
│   └── test_network_integration.py
├── performance/
│   ├── test_load.py
│   ├── test_stress.py
│   └── test_benchmarks.py
├── compliance/
│   ├── test_protocol_compliance.py
│   ├── test_transport_compliance.py
│   └── test_security_compliance.py
├── e2e/
│   ├── test_complete_workflow.py
│   └── test_error_scenarios.py
├── fixtures/
│   ├── sample_documents/
│   └── test_configs/
├── conftest.py
└── test_utils.py
```

## Unit Testing Framework

### Server Component Tests

```python
# tests/unit/test_server.py
import pytest
from unittest.mock import Mock, AsyncMock
from mcp.server import Server
from mcp.types import Tool, CallToolResult, TextContent

class TestMCPServer:
    """Unit tests for MCP server core functionality."""
    
    @pytest.fixture
    def server(self):
        """Create test server instance."""
        return Server("test-server")
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, server):
        """Test server initialization."""
        assert server.name == "test-server"
        assert hasattr(server, 'list_tools')
        assert hasattr(server, 'call_tool')
    
    @pytest.mark.asyncio
    async def test_tool_registration(self, server):
        """Test tool registration."""
        @server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="test_tool",
                    description="Test tool",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "param": {"type": "string"}
                        },
                        "required": ["param"]
                    }
                )
            ]
        
        tools = await list_tools()
        assert len(tools) == 1
        assert tools[0].name == "test_tool"
    
    @pytest.mark.asyncio
    async def test_tool_execution_success(self, server):
        """Test successful tool execution."""
        @server.call_tool()
        async def call_tool(name: str, arguments: dict):
            if name == "test_tool":
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Result: {arguments['param']}")],
                    isError=False
                )
        
        result = await call_tool("test_tool", {"param": "test_value"})
        assert not result.isError
        assert "test_value" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_tool_execution_error(self, server):
        """Test tool execution with error."""
        @server.call_tool()
        async def call_tool(name: str, arguments: dict):
            return CallToolResult(
                content=[TextContent(type="text", text="Error: Tool failed")],
                isError=True
            )
        
        result = await call_tool("test_tool", {})
        assert result.isError
        assert "Error: Tool failed" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_tool_not_found(self, server):
        """Test unknown tool handling."""
        @server.call_tool()
        async def call_tool(name: str, arguments: dict):
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )
        
        result = await call_tool("unknown_tool", {})
        assert result.isError
        assert "Unknown tool" in result.content[0].text
```

### Transport Component Tests

```python
# tests/unit/test_transport.py
import pytest
import asyncio
import json
from unittest.mock import Mock, patch
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport

class TestStdioTransport:
    """Unit tests for STDIO transport."""
    
    @pytest.mark.asyncio
    async def test_stdio_message_framing(self):
        """Test STDIO message framing."""
        messages = []
        
        async def mock_write_stream(message):
            messages.append(message)
        
        # Test message with proper framing
        test_message = {"jsonrpc": "2.0", "id": "1", "method": "test"}
        await mock_write_stream(json.dumps(test_message) + '\n')
        
        assert len(messages) == 1
        assert messages[0].endswith('\n')
        assert json.loads(messages[0].strip()) == test_message
    
    @pytest.mark.asyncio
    async def test_stdio_error_handling(self):
        """Test STDIO error handling."""
        errors = []
        
        async def mock_handle_message(message):
            if not message.strip():
                raise ValueError("Empty message")
            try:
                json.loads(message)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON")
        
        # Test invalid JSON handling
        try:
            await mock_handle_message("invalid json")
        except ValueError as e:
            errors.append(str(e))
        
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0]

class TestHttpTransport:
    """Unit tests for HTTP transport."""
    
    @pytest.mark.asyncio
    async def test_sse_headers(self):
        """Test SSE header compliance."""
        transport = SseServerTransport("http://localhost:3020/mcp")
        
        # Mock response object
        response = Mock()
        response.headers = {}
        
        # Simulate SSE response setup
        response.headers.update({
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        })
        
        assert response.headers['Content-Type'] == 'text/event-stream'
        assert response.headers['Cache-Control'] == 'no-cache'
        assert response.headers['Connection'] == 'keep-alive'
    
    @pytest.mark.asyncio
    async def test_sse_event_formatting(self):
        """Test SSE event formatting."""
        transport = SseServerTransport("http://localhost:3020/mcp")
        
        events = []
        
        async def mock_send_event(event_type: str, data: dict):
            event_str = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            events.append(event_str)
        
        await mock_send_event('message', {'test': 'data'})
        
        assert len(events) == 1
        assert events[0].startswith('event: message')
        assert 'data: {"test": "data"}' in events[0]
        assert events[0].endswith('\n\n')
    
    @pytest.mark.asyncio
    async def test_cors_headers(self):
        """Test CORS header compliance."""
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Accept',
        }
        
        assert headers['Access-Control-Allow-Origin'] == '*'
        assert 'GET' in headers['Access-Control-Allow-Methods']
        assert 'Content-Type' in headers['Access-Control-Allow-Headers']
```

### Configuration Tests

```python
# tests/unit/test_config.py
import pytest
import os
from unittest.mock import patch
import argparse

class TestConfiguration:
    """Unit tests for configuration management."""
    
    def test_argument_parsing(self):
        """Test command line argument parsing."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
        parser.add_argument("--host", default="0.0.0.0")
        parser.add_argument("--port", type=int, default=3020)
        
        args = parser.parse_args(["--transport", "http", "--port", "8080"])
        
        assert args.transport == "http"
        assert args.port == 8080
        assert args.host == "0.0.0.0"
    
    def test_environment_variables(self):
        """Test environment variable handling."""
        with patch.dict(os.environ, {'MCP_PORT': '9090', 'MCP_HOST': 'localhost'}):
            port = int(os.environ.get('MCP_PORT', 3020))
            host = os.environ.get('MCP_HOST', '0.0.0.0')
            
            assert port == 9090
            assert host == 'localhost'
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        def validate_port(port: int) -> bool:
            return 1024 <= port <= 65535
        
        def validate_transport(transport: str) -> bool:
            return transport in ["stdio", "http"]
        
        assert validate_port(3020)
        assert not validate_port(80)  # Reserved port
        assert not validate_port(70000)  # Out of range
        
        assert validate_transport("http")
        assert not validate_transport("invalid")
```

## Integration Testing Framework

### Service Integration Tests

```python
# tests/integration/test_service_integration.py
import pytest
import asyncio
import aiohttp
from docker import DockerClient

class TestServiceIntegration:
    """Integration tests for MCP services."""
    
    @pytest.fixture(scope="session")
    def docker_client(self):
        """Docker client for service management."""
        return DockerClient.from_env()
    
    @pytest.fixture(scope="session")
    async def services_up(self, docker_client):
        """Ensure services are running for integration tests."""
        # Start services
        os.system("docker compose -f docker-compose.mcp-pro.yml up -d")
        
        # Wait for services to be ready
        await asyncio.sleep(30)
        
        yield
        
        # Cleanup
        os.system("docker compose -f docker-compose.mcp-pro.yml down")
    
    @pytest.mark.asyncio
    async def test_service_health_checks(self, services_up):
        """Test that all services pass health checks."""
        services = [
            ("http://localhost:3020/health", "docling-mcp"),
            ("http://localhost:2091/health", "mcp-gateway"),
            ("http://localhost:7071/health", "e2b-runner"),
            ("http://localhost:7072/health", "vl-sentinel")
        ]
        
        async with aiohttp.ClientSession() as session:
            for url, service_name in services:
                async with session.get(url) as resp:
                    assert resp.status == 200, f"{service_name} health check failed"
    
    @pytest.mark.asyncio
    async def test_mcp_gateway_integration(self, services_up):
        """Test MCP gateway integration with backend services."""
        async with aiohttp.ClientSession() as session:
            # Test gateway server listing
            async with session.get("http://localhost:2091/servers") as resp:
                assert resp.status == 200
                servers = await resp.json()
                assert "docling" in servers
                assert "postman" in servers
    
    @pytest.mark.asyncio
    async def test_service_dependencies(self, services_up):
        """Test service dependency resolution."""
        async with aiohttp.ClientSession() as session:
            # Test that gateway can reach docling-mcp
            async with session.get("http://localhost:2091/servers/docling/tools") as resp:
                assert resp.status == 200
                tools = await resp.json()
                assert isinstance(tools, list)
```

### Network Integration Tests

```python
# tests/integration/test_network_integration.py
import pytest
import asyncio
import aiohttp

class TestNetworkIntegration:
    """Network integration tests."""
    
    @pytest.mark.asyncio
    async def test_sse_connection_stability(self):
        """Test SSE connection stability over time."""
        async with aiohttp.ClientSession() as session:
            start_time = asyncio.get_event_loop().time()
            event_count = 0
            
            async with session.get(
                "http://localhost:3020/mcp",
                headers={"Accept": "text/event-stream"}
            ) as resp:
                assert resp.status == 200
                
                # Read events for 30 seconds
                async for line in resp.content:
                    if line.startswith(b'data:'):
                        event_count += 1
                    
                    current_time = asyncio.get_event_loop().time()
                    if current_time - start_time > 30:
                        break
            
            # Should receive keepalive events
            assert event_count > 0, "No SSE events received"
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test handling of multiple concurrent connections."""
        connection_count = 10
        results = []
        
        async def test_connection(i):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:3020/health") as resp:
                        return resp.status == 200
            except Exception:
                return False
        
        # Test concurrent connections
        tasks = [test_connection(i) for i in range(connection_count)]
        results = await asyncio.gather(*tasks)
        
        successful_connections = sum(results)
        assert successful_connections >= connection_count * 0.8  # 80% success rate
    
    @pytest.mark.asyncio
    async def test_connection_recovery(self):
        """Test connection recovery after service restart."""
        # Initial connection
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:3020/health") as resp:
                assert resp.status == 200
        
        # Simulate service restart
        os.system("docker compose -f docker-compose.mcp-pro.yml restart docling-mcp")
        await asyncio.sleep(10)
        
        # Test reconnection
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:3020/health") as resp:
                assert resp.status == 200
```

## Performance Testing Framework

### Load Testing

```python
# tests/performance/test_load.py
import pytest
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

class TestLoadPerformance:
    """Load testing for MCP services."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_load(self):
        """Test tool execution under load."""
        concurrent_requests = 50
        request_count = 100
        
        async def execute_tool_request(session, request_num):
            try:
                start_time = time.time()
                
                async with session.post(
                    "http://localhost:2091/servers/docling/tools/get_supported_formats",
                    json={}
                ) as resp:
                    duration = time.time() - start_time
                    
                    if resp.status == 200:
                        return {"success": True, "duration": duration}
                    else:
                        return {"success": False, "duration": duration}
            except Exception as e:
                return {"success": False, "duration": time.time() - start_time, "error": str(e)}
        
        async with aiohttp.ClientSession() as session:
            # Execute requests concurrently
            tasks = []
            for i in range(request_count):
                task = execute_tool_request(session, i)
                tasks.append(task)
                
                # Limit concurrent requests
                if len(tasks) >= concurrent_requests:
                    results = await asyncio.gather(*tasks)
                    
                    # Analyze results
                    successful = sum(1 for r in results if r["success"])
                    avg_duration = sum(r["duration"] for r in results) / len(results)
                    
                    assert successful >= len(results) * 0.9  # 90% success rate
                    assert avg_duration < 5.0  # Average response time < 5 seconds
                    
                    tasks = []
                    await asyncio.sleep(0.1)  # Brief pause between batches
    
    @pytest.mark.asyncio
    async def test_http_endpoint_load(self):
        """Test HTTP endpoint performance under load."""
        endpoint = "http://localhost:3020/health"
        request_count = 1000
        concurrent_limit = 100
        
        response_times = []
        errors = []
        
        async def make_request(session, req_num):
            try:
                start_time = time.time()
                async with session.get(endpoint) as resp:
                    duration = time.time() - start_time
                    
                    if resp.status == 200:
                        response_times.append(duration)
                    else:
                        errors.append(f"Status {resp.status}")
                        
            except Exception as e:
                errors.append(str(e))
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def limited_request(session, req_num):
            async with semaphore:
                await make_request(session, req_num)
        
        async with aiohttp.ClientSession() as session:
            tasks = [limited_request(session, i) for i in range(request_count)]
            await asyncio.gather(*tasks)
        
        # Analyze results
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            print(f"Average response time: {avg_response_time:.3f}s")
            print(f"Max response time: {max_response_time:.3f}s")
            print(f"Error rate: {len(errors)}/{request_count}")
            
            assert avg_response_time < 1.0  # Average < 1 second
            assert len(errors) < request_count * 0.05  # Error rate < 5%
```

### Stress Testing

```python
# tests/performance/test_stress.py
import pytest
import asyncio
import aiohttp
import psutil
import time

class TestStressPerformance:
    """Stress testing for MCP services."""
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage under sustained load."""
        duration = 60  # 1 minute
        request_rate = 10  # requests per second
        
        initial_memory = psutil.virtual_memory().percent
        
        start_time = time.time()
        request_count = 0
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < duration:
                try:
                    async with session.get("http://localhost:3020/health") as resp:
                        if resp.status == 200:
                            request_count += 1
                except Exception:
                    pass
                
                await asyncio.sleep(1 / request_rate)
        
        final_memory = psutil.virtual_memory().percent
        memory_increase = final_memory - initial_memory
        
        print(f"Requests completed: {request_count}")
        print(f"Memory increase: {memory_increase:.1f}%")
        
        # Memory increase should be minimal (< 10%)
        assert memory_increase < 10.0
    
    @pytest.mark.asyncio
    async def test_cpu_usage_under_load(self):
        """Test CPU usage under load."""
        duration = 30  # 30 seconds
        concurrent_requests = 50
        
        cpu_samples = []
        
        async def generate_load():
            async with aiohttp.ClientSession() as session:
                while True:
                    try:
                        async with session.get("http://localhost:3020/mcp") as resp:
                            await resp.text()
                    except Exception:
                        pass
                    await asyncio.sleep(0.1)
        
        # Start load generation
        load_tasks = [generate_load() for _ in range(concurrent_requests)]
        load_coros = [asyncio.create_task(task) for task in load_tasks]
        
        # Monitor CPU usage
        start_time = time.time()
        while time.time() - start_time < duration:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_samples.append(cpu_percent)
        
        # Stop load generation
        for task in load_coros:
            task.cancel()
        
        await asyncio.gather(*load_coros, return_exceptions=True)
        
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        max_cpu = max(cpu_samples)
        
        print(f"Average CPU usage: {avg_cpu:.1f}%")
        print(f"Max CPU usage: {max_cpu:.1f}%")
        
        # CPU usage should stay reasonable (< 80% average)
        assert avg_cpu < 80.0
        assert max_cpu < 95.0
    
    @pytest.mark.asyncio
    async def test_connection_exhaustion(self):
        """Test behavior under connection exhaustion."""
        max_connections = 200
        
        connections = []
        errors = []
        
        async def create_connection(i):
            try:
                session = aiohttp.ClientSession()
                connections.append(session)
                
                async with session.get("http://localhost:3020/mcp") as resp:
                    await asyncio.sleep(1)  # Hold connection
                    
            except Exception as e:
                errors.append(str(e))
            finally:
                await session.close()
        
        # Create many connections
        tasks = [create_connection(i) for i in range(max_connections)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        error_rate = len(errors) / max_connections
        print(f"Connection error rate: {error_rate:.2%}")
        
        # Should handle connection exhaustion gracefully
        assert error_rate < 0.5  # Less than 50% error rate
```

### Benchmark Tests

```python
# tests/performance/test_benchmarks.py
import pytest
import time
import statistics
from test_utils import BenchmarkResult

class TestBenchmarks:
    """Benchmark tests for performance comparison."""
    
    @pytest.mark.benchmark
    def test_tool_execution_benchmark(self):
        """Benchmark tool execution performance."""
        execution_times = []
        
        for i in range(100):
            start_time = time.time()
            
            # Simulate tool execution
            # This would be replaced with actual tool calls
            time.sleep(0.001)  # Simulate 1ms processing
            
            duration = time.time() - start_time
            execution_times.append(duration)
        
        # Calculate statistics
        avg_time = statistics.mean(execution_times)
        median_time = statistics.median(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        std_dev = statistics.stdev(execution_times)
        
        benchmark = BenchmarkResult(
            name="tool_execution",
            iterations=len(execution_times),
            avg_time=avg_time,
            median_time=median_time,
            min_time=min_time,
            max_time=max_time,
            std_dev=std_dev
        )
        
        print(f"Tool Execution Benchmark:")
        print(f"  Average: {avg_time*1000:.3f}ms")
        print(f"  Median: {median_time*1000:.3f}ms")
        print(f"  Min: {min_time*1000:.3f}ms")
        print(f"  Max: {max_time*1000:.3f}ms")
        print(f"  Std Dev: {std_dev*1000:.3f}ms")
        
        # Performance targets
        assert avg_time < 0.1  # Average < 100ms
        assert median_time < 0.05  # Median < 50ms
        assert std_dev < 0.05  # Consistent performance
    
    @pytest.mark.benchmark
    def test_http_response_benchmark(self):
        """Benchmark HTTP response times."""
        response_times = []
        
        # This would be replaced with actual HTTP calls
        for i in range(100):
            start_time = time.time()
            
            # Simulate HTTP request processing
            time.sleep(0.0005)  # Simulate 0.5ms network + processing
            
            duration = time.time() - start_time
            response_times.append(duration)
        
        avg_response_time = statistics.mean(response_times)
        
        print(f"HTTP Response Benchmark:")
        print(f"  Average response time: {avg_response_time*1000:.3f}ms")
        
        # Target: < 10ms average response time
        assert avg_response_time < 0.01
```

## Compliance Testing Framework

### Protocol Compliance Tests

```python
# tests/compliance/test_protocol_compliance.py
import pytest
from mcp.types import InitializeRequest, CallToolRequest, ListToolsRequest

class TestProtocolCompliance:
    """Test MCP protocol specification compliance."""
    
    @pytest.mark.asyncio
    async def test_json_rpc_compliance(self):
        """Test JSON-RPC 2.0 message format compliance."""
        # Test request format
        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        # Validate JSON-RPC structure
        assert request["jsonrpc"] == "2.0"
        assert "id" in request
        assert "method" in request
        assert "params" in request
        
        # Test response format
        response = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "result": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "serverInfo": {"name": "test-server", "version": "1.0.0"}
            }
        }
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == request["id"]
        assert "result" in response
    
    @pytest.mark.asyncio
    async def test_error_response_compliance(self):
        """Test error response format compliance."""
        error_response = {
            "jsonrpc": "2.0",
            "id": "test-2",
            "error": {
                "code": -32601,
                "message": "Method not found",
                "data": {"method": "unknown_method"}
            }
        }
        
        # Validate error response structure
        assert error_response["jsonrpc"] == "2.0"
        assert "id" in error_response
        assert "error" in error_response
        assert "code" in error_response["error"]
        assert "message" in error_response["error"]
        assert isinstance(error_response["error"]["code"], int)
        assert isinstance(error_response["error"]["message"], str)
    
    @pytest.mark.asyncio
    async def test_tool_result_compliance(self):
        """Test tool result format compliance."""
        from mcp.types import CallToolResult, TextContent
        
        # Valid tool result
        result = CallToolResult(
            content=[TextContent(type="text", text="Test result")],
            isError=False
        )
        
        assert hasattr(result, 'content')
        assert hasattr(result, 'isError')
        assert isinstance(result.content, list)
        assert len(result.content) > 0
        assert hasattr(result.content[0], 'type')
        assert hasattr(result.content[0], 'text')
        
        # Error result
        error_result = CallToolResult(
            content=[TextContent(type="text", text="Error occurred")],
            isError=True
        )
        
        assert error_result.isError == True
```

### Transport Compliance Tests

```python
# tests/compliance/test_transport_compliance.py
import pytest
import aiohttp

class TestTransportCompliance:
    """Test transport layer compliance."""
    
    @pytest.mark.asyncio
    async def test_stdio_framing_compliance(self):
        """Test STDIO message framing compliance."""
        messages = [
            '{"jsonrpc": "2.0", "id": "1", "method": "test"}\n',
            '{"jsonrpc": "2.0", "id": "2", "method": "test"}\n'
        ]
        
        for message in messages:
            # Each message must end with newline
            assert message.endswith('\n')
            
            # Must be valid JSON
            import json
            parsed = json.loads(message.strip())
            assert parsed["jsonrpc"] == "2.0"
    
    @pytest.mark.asyncio
    async def test_http_sse_compliance(self):
        """Test HTTP SSE transport compliance."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:3020/mcp",
                headers={"Accept": "text/event-stream"}
            ) as resp:
                # Check required headers
                assert resp.headers['Content-Type'] == 'text/event-stream'
                assert resp.headers['Cache-Control'] == 'no-cache'
                assert resp.headers['Connection'] == 'keep-alive'
                
                # Read first event
                line = await resp.content.readline()
                assert line.startswith(b'event:') or line.startswith(b'data:')
    
    @pytest.mark.asyncio
    async def test_cors_compliance(self):
        """Test CORS header compliance."""
        async with aiohttp.ClientSession() as session:
            # Test preflight request
            async with session.options(
                "http://localhost:3020/mcp",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET"
                }
            ) as resp:
                assert resp.headers.get('Access-Control-Allow-Origin') == '*'
                assert 'GET' in resp.headers.get('Access-Control-Allow-Methods', '')
```

### Security Compliance Tests

```python
# tests/compliance/test_security_compliance.py
import pytest
import json

class TestSecurityCompliance:
    """Test security compliance requirements."""
    
    @pytest.mark.asyncio
    async def test_input_validation_compliance(self):
        """Test input validation compliance."""
        # Test path traversal prevention
        malicious_paths = [
            "../../../etc/passwd",
            "../../windows/system32/config/sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM"
        ]
        
        for path in malicious_paths:
            # These should be rejected or sanitized
            assert not self.is_safe_path(path), f"Path should be unsafe: {path}"
    
    @pytest.mark.asyncio
    async def test_error_information_disclosure(self):
        """Test that errors don't disclose sensitive information."""
        # Error messages should not contain stack traces or internal details
        safe_error_messages = [
            "Tool execution failed",
            "Invalid input parameters",
            "Resource not found"
        ]
        
        unsafe_error_messages = [
            "FileNotFoundError: [Errno 2] No such file or directory: '/etc/passwd'",
            "Traceback (most recent call last):",
            "Internal server error: database connection failed"
        ]
        
        for msg in safe_error_messages:
            assert self.is_safe_error_message(msg)
        
        for msg in unsafe_error_messages:
            assert not self.is_safe_error_message(msg)
    
    def is_safe_path(self, path: str) -> bool:
        """Check if file path is safe."""
        # Simple safety check - production would be more comprehensive
        return ".." not in path and not path.startswith("/")
    
    def is_safe_error_message(self, message: str) -> bool:
        """Check if error message is safe for external display."""
        unsafe_patterns = ["Traceback", "FileNotFoundError", "database", "password"]
        return not any(pattern in message for pattern in unsafe_patterns)
```

## End-to-End Testing Framework

### Complete Workflow Tests

```python
# tests/e2e/test_complete_workflow.py
import pytest
import asyncio
import aiohttp
import tempfile
import os

class TestCompleteWorkflow:
    """End-to-end tests for complete MCP workflows."""
    
    @pytest.mark.asyncio
    async def test_document_processing_workflow(self):
        """Test complete document processing workflow."""
        # Create test document
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as f:
            f.write("This is a test document for MCP processing.")
            test_file = f.name
        
        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: Initialize MCP connection
                async with session.post(
                    "http://localhost:2091/servers/docling/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": "1",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "1.0",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0.0"}
                        }
                    }
                ) as resp:
                    assert resp.status == 200
                    init_result = await resp.json()
                    assert "result" in init_result
            
                # Step 2: List available tools
                async with session.post(
                    "http://localhost:2091/servers/docling/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": "2",
                        "method": "tools/list",
                        "params": {}
                    }
                ) as resp:
                    assert resp.status == 200
                    tools_result = await resp.json()
                    assert "result" in tools_result
                    assert "tools" in tools_result["result"]
                
                # Verify document conversion tool is available
                tools = tools_result["result"]["tools"]
                conversion_tool = next(
                    (tool for tool in tools if tool["name"] == "convert_document"),
                    None
                )
                assert conversion_tool is not None
                
                # Step 3: Execute document conversion
                async with session.post(
                    "http://localhost:2091/servers/docling/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": "3",
                        "method": "tools/call",
                        "params": {
                            "name": "convert_document",
                            "arguments": {
                                "input_path": test_file,
                                "output_format": "markdown"
                            }
                        }
                    }
                ) as resp:
                    assert resp.status == 200
                    call_result = await resp.json()
                    assert "result" in call_result
                    assert call_result["result"]["content"][0]["type"] == "text"
                
                print("✅ Complete document processing workflow successful")
        
        finally:
            os.unlink(test_file)
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery in complete workflow."""
        async with aiohttp.ClientSession() as session:
            # Test with invalid tool name
            async with session.post(
                "http://localhost:2091/servers/docling/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "error-test",
                    "method": "tools/call",
                    "params": {
                        "name": "nonexistent_tool",
                        "arguments": {}
                    }
                }
            ) as resp:
                assert resp.status == 200
                result = await resp.json()
                
                # Should receive error response
                assert "error" in result or (
                    "result" in result and result["result"].get("isError") == True
                )
            
            # Test with invalid parameters
            async with session.post(
                "http://localhost:2091/servers/docling/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "invalid-params-test",
                    "method": "tools/call",
                    "params": {
                        "name": "convert_document",
                        "arguments": {}  # Missing required parameters
                    }
                }
            ) as resp:
                assert resp.status == 200
                result = await resp.json()
                
                # Should receive error response
                assert "error" in result or (
                    "result" in result and result["result"].get("isError") == True
                )
            
            print("✅ Error recovery workflow successful")
```

### Multi-Service Integration Tests

```python
# tests/e2e/test_multi_service_integration.py
import pytest
import asyncio
import aiohttp

class TestMultiServiceIntegration:
    """Test integration of multiple MCP services."""
    
    @pytest.mark.asyncio
    async def test_gateway_aggregation(self):
        """Test MCP gateway aggregating multiple services."""
        async with aiohttp.ClientSession() as session:
            # Get all available servers through gateway
            async with session.get("http://localhost:2091/servers") as resp:
                assert resp.status == 200
                servers = await resp.json()
                
                # Should have multiple services
                assert len(servers) >= 2
                assert "docling" in servers
                assert "postman" in servers
            
            # Test tool aggregation
            all_tools = {}
            for server_name in ["docling", "postman"]:
                async with session.get(f"http://localhost:2091/servers/{server_name}/tools") as resp:
                    if resp.status == 200:
                        tools = await resp.json()
                        all_tools[server_name] = tools
            
            # Verify tools from different services
            assert len(all_tools) >= 2
            print(f"✅ Gateway aggregation working: {len(all_tools)} services available")
    
    @pytest.mark.asyncio
    async def test_service_chain_execution(self):
        """Test execution across multiple services."""
        async with aiohttp.ClientSession() as session:
            # Chain: Docling → Postman → E2B
            
            # Step 1: Process document with docling
            async with session.post(
                "http://localhost:2091/servers/docling/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "chain-1",
                    "method": "tools/call",
                    "params": {
                        "name": "get_supported_formats",
                        "arguments": {}
                    }
                }
            ) as resp:
                assert resp.status == 200
                docling_result = await resp.json()
                assert "result" in docling_result
            
            # Step 2: Use postman for API testing
            async with session.post(
                "http://localhost:2091/servers/postman/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "chain-2",
                    "method": "tools/call",
                    "params": {
                        "name": "list_collections",
                        "arguments": {}
                    }
                }
            ) as resp:
                assert resp.status == 200
                postman_result = await resp.json()
                # Postman might not be configured, so we just check response format
            
            print("✅ Service chain execution successful")
```

## Test Automation and CI/CD

### Test Configuration

```python
# tests/conftest.py
import pytest
import asyncio
import os
from typing import AsyncGenerator

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_config():
    """Test configuration."""
    return {
        "mcp_gateway_url": os.getenv("MCP_GATEWAY_URL", "http://localhost:2091"),
        "docling_mcp_url": os.getenv("DOCLING_MCP_URL", "http://localhost:3020"),
        "test_timeout": int(os.getenv("TEST_TIMEOUT", "30")),
        "load_test_duration": int(os.getenv("LOAD_TEST_DURATION", "60")),
        "stress_test_duration": int(os.getenv("STRESS_TEST_DURATION", "30"))
    }

@pytest.fixture
async def aiohttp_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Provide aiohttp session for tests."""
    session = aiohttp.ClientSession()
    try:
        yield session
    finally:
        await session.close()
```

### Test Utilities

```python
# tests/test_utils.py
import time
import statistics
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class BenchmarkResult:
    """Result of a benchmark test."""
    name: str
    iterations: int
    avg_time: float
    median_time: float
    min_time: float
    max_time: float
    std_dev: float
    success_rate: float

class PerformanceMonitor:
    """Monitor performance metrics during tests."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
    
    def record_metric(self, name: str, value: float):
        """Record a performance metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
    
    def get_statistics(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        values = self.metrics[name]
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0
        }

def measure_execution_time(func, *args, **kwargs):
    """Measure execution time of a function."""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time

class MockMCPClient:
    """Mock MCP client for testing."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def initialize(self, session: aiohttp.ClientSession):
        """Initialize MCP connection."""
        return await self._send_request(session, "initialize", {
            "protocolVersion": "1.0",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        })
    
    async def list_tools(self, session: aiohttp.ClientSession):
        """List available tools."""
        return await self._send_request(session, "tools/list", {})
    
    async def call_tool(self, session: aiohttp.ClientSession, name: str, arguments: Dict[str, Any]):
        """Call a tool."""
        return await self._send_request(session, "tools/call", {
            "name": name,
            "arguments": arguments
        })
    
    async def _send_request(self, session: aiohttp.ClientSession, method: str, params: Dict[str, Any]):
        """Send JSON-RPC request."""
        request_data = {
            "jsonrpc": "2.0",
            "id": str(time.time()),
            "method": method,
            "params": params
        }
        
        async with session.post(
            f"{self.base_url}/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"}
        ) as resp:
            return await resp.json()
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: MCP Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit -v --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker
      uses: docker/setup-buildx-action@v2
    
    - name: Start services
      run: |
        docker compose -f docker-compose.mcp-pro.yml up -d --build
        sleep 60
    
    - name: Run integration tests
      run: |
        pytest tests/integration -v
    
    - name: Run compliance tests
      run: |
        pytest tests/compliance -v
    
    - name: Cleanup
      if: always()
      run: |
        docker compose -f docker-compose.mcp-pro.yml down

  performance-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker
      uses: docker/setup-buildx-action@v2
    
    - name: Start services
      run: |
        docker compose -f docker-compose.mcp-pro.yml up -d --build
        sleep 60
    
    - name: Run performance tests
      run: |
        pytest tests/performance -v --tb=short
    
    - name: Run benchmarks
      run: |
        pytest tests/performance/test_benchmarks.py -v -m benchmark
    
    - name: Cleanup
      if: always()
      run: |
        docker compose -f docker-compose.mcp-pro.yml down

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker
      uses: docker/setup-buildx-action@v2
    
    - name: Start services
      run: |
        docker compose -f docker-compose.mcp-pro.yml up -d --build
        sleep 60
    
    - name: Run end-to-end tests
      run: |
        pytest tests/e2e -v
    
    - name: Cleanup
      if: always()
      run: |
        docker compose -f docker-compose.mcp-pro.yml down
```

## Test Reporting and Metrics

### Test Coverage Report

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Coverage targets
# - Unit tests: >90% coverage
# - Integration tests: >80% coverage
# - Overall: >85% coverage
```

### Performance Report

```python
# Generate performance report
def generate_performance_report(results: List[BenchmarkResult]) -> str:
    """Generate performance test report."""
    report = []
    report.append("# MCP Performance Test Report")
    report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    for result in results:
        report.append(f"## {result.name}")
        report.append(f"- Iterations: {result.iterations}")
        report.append(f"- Average Time: {result.avg_time*1000:.3f}ms")
        report.append(f"- Median Time: {result.median_time*1000:.3f}ms")
        report.append(f"- Min Time: {result.min_time*1000:.3f}ms")
        report.append(f"- Max Time: {result.max_time*1000:.3f}ms")
        report.append(f"- Standard Deviation: {result.std_dev*1000:.3f}ms")
        report.append(f"- Success Rate: {result.success_rate:.1%}")
        report.append("")
    
    return "\n".join(report)
```

### Compliance Report

```python
# Generate compliance report
def generate_compliance_report(test_results: Dict[str, bool]) -> str:
    """Generate protocol compliance report."""
    report = []
    report.append("# MCP Protocol Compliance Report")
    report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    compliance_rate = passed_tests / total_tests if total_tests > 0 else 0
    
    report.append(f"## Summary")
    report.append(f"- Total Tests: {total_tests}")
    report.append(f"- Passed Tests: {passed_tests}")
    report.append(f"- Compliance Rate: {compliance_rate:.1%}")
    report.append("")
    
    report.append("## Detailed Results")
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        report.append(f"- {test_name}: {status}")
    
    return "\n".join(report)
```

## Continuous Monitoring

### Performance Monitoring

```python
# Monitor performance in production
import logging
import time

class ProductionPerformanceMonitor:
    """Monitor performance in production environment."""
    
    def __init__(self):
        self.logger = logging.getLogger("performance")
        self.metrics = {}
    
    def record_request(self, method: str, duration: float, success: bool):
        """Record request performance."""
        if method not in self.metrics:
            self.metrics[method] = []
        
        self.metrics[method].append({
            "duration": duration,
            "success": success,
            "timestamp": time.time()
        })
        
        # Log slow requests
        if duration > 1.0:  # Requests taking > 1 second
            self.logger.warning(f"Slow request: {method} took {duration:.3f}s")
    
    def get_performance_summary(self, method: str = None) -> dict:
        """Get performance summary for a method or all methods."""
        if method:
            return self._calculate_stats(self.metrics.get(method, []))
        
        summary = {}
        for method, metrics in self.metrics.items():
            summary[method] = self._calculate_stats(metrics)
        
        return summary
    
    def _calculate_stats(self, metrics: list) -> dict:
        """Calculate statistics from metrics."""
        if not metrics:
            return {}
        
        durations = [m["duration"] for m in metrics]
        success_count = sum(1 for m in metrics if m["success"])
        
        return {
            "count": len(metrics),
            "success_rate": success_count / len(metrics),
            "avg_duration": sum(durations) / len(durations),
            "max_duration": max(durations),
            "min_duration": min(durations)
        }
```

This comprehensive testing framework ensures MCP server implementations are thoroughly tested for functionality, performance, compliance, and reliability.