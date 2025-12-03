#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Docling MCP Server

This module contains integration tests for the docling-mcp service implementation,
covering HTTP/SSE transport, STDIO transport, MCP protocol compliance, tool execution,
error handling, and custom SSE handler functionality.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable, Awaitable
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

import aiohttp
import pytest
from aiohttp import web

# Add the parent directory to the path to import the docling_mcp_server
sys.path.insert(0, str(Path(__file__).parent.parent))

from docling_mcp_server import DoclingMCPServer, create_custom_sse_handler


# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestDoclingMCPIntegration:
    """Comprehensive integration tests for Docling MCP Server."""

    @pytest.fixture
    def server(self) -> DoclingMCPServer:
        """Create a Docling MCP server instance for testing."""
        return DoclingMCPServer("test-docling-mcp")

    @pytest.fixture
    def temp_document(self) -> str:
        """Create a temporary test document."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test document for Docling MCP integration testing.")
            temp_path: str = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    async def http_client(self) -> AsyncGenerator[aiohttp.ClientSession, None]:
        """Create an aiohttp client session for testing."""
        async with aiohttp.ClientSession() as session:
            yield session

    @pytest.mark.asyncio
    async def test_server_initialization(self, server: DoclingMCPServer) -> None:
        """Test server initialization and basic setup."""
        assert server.server is not None
        assert server.server.name == "test-docling-mcp"
        logger.info("✓ Server initialization test passed")

    @pytest.mark.asyncio
    async def test_list_tools(self, server: DoclingMCPServer) -> None:
        """Test tool listing functionality."""
        # Get the list_tools handler
        list_tools_handler: Optional[Callable[[], Awaitable[ListToolsResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'list_tools':
                list_tools_handler = handler
                break
        
        assert list_tools_handler is not None, "list_tools handler not found"
        
        # Call the handler
        result: ListToolsResult = await list_tools_handler()
        
        assert hasattr(result, 'tools')
        assert len(result.tools) >= 1  # At least health_check should be available
        
        # Check for expected tools
        tool_names: List[str] = [tool.name for tool in result.tools]
        assert 'health_check' in tool_names
        
        logger.info(f"✓ List tools test passed - found tools: {tool_names}")

    @pytest.mark.asyncio
    async def test_health_check_tool(self, server: DoclingMCPServer) -> None:
        """Test health check tool execution."""
        # Get the call_tool handler
        call_tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[CallToolResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        assert call_tool_handler is not None, "call_tool handler not found"
        
        # Test health check
        result: CallToolResult = await call_tool_handler("health_check", {})
        
        assert hasattr(result, 'content')
        assert len(result.content) == 1
        assert result.content[0].type == "text"
        assert "healthy" in result.content[0].text.lower()
        
        logger.info("✓ Health check tool test passed")

    @pytest.mark.asyncio
    async def test_convert_document_tool_missing_file(self, server: DoclingMCPServer) -> None:
        """Test convert_document tool with missing file."""
        call_tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[CallToolResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        # Test with non-existent file
        result: CallToolResult = await call_tool_handler("convert_document", {
            "file_path": "/non/existent/file.pdf"
        })
        
        assert result.isError is True
        assert hasattr(result, 'content')
        assert "not found" in result.content[0].text.lower()
        
        logger.info("✓ Convert document missing file test passed")

    @pytest.mark.asyncio
    async def test_convert_document_tool_valid_file(self, server: DoclingMCPServer, temp_document: str) -> None:
        """Test convert_document tool with valid file."""
        call_tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[CallToolResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        # Test with valid file
        result: CallToolResult = await call_tool_handler("convert_document", {
            "file_path": temp_document,
            "output_format": "text"
        })
        
        # Result depends on whether docling is available
        if hasattr(result, 'isError') and result.isError:
            # If docling is not available, we should get an appropriate error
            assert "docling" in result.content[0].text.lower()
        else:
            # If docling is available, we should get converted content
            assert hasattr(result, 'content')
            assert len(result.content) == 1
            assert "test document" in result.content[0].text.lower()
        
        logger.info("✓ Convert document valid file test passed")

    @pytest.mark.asyncio
    async def test_process_documents_batch_tool(self, server: DoclingMCPServer, temp_document: str) -> None:
        """Test process_documents_batch tool."""
        call_tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[CallToolResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        # Test batch processing
        result: CallToolResult = await call_tool_handler("process_documents_batch", {
            "file_paths": [temp_document],
            "output_format": "text"
        })
        
        # Result depends on whether docling is available
        if hasattr(result, 'isError') and result.isError:
            # If docling is not available, we should get an appropriate error
            assert "docling" in result.content[0].text.lower()
        else:
            # If docling is available, we should get processed content
            assert hasattr(result, 'content')
            assert len(result.content) == 1
        
        logger.info("✓ Process documents batch test passed")

    @pytest.mark.asyncio
    async def test_unknown_tool(self, server: DoclingMCPServer) -> None:
        """Test calling an unknown tool."""
        call_tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[CallToolResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        # Test unknown tool
        result: CallToolResult = await call_tool_handler("unknown_tool", {})
        
        assert result.isError is True
        assert "unknown tool" in result.content[0].text.lower()
        
        logger.info("✓ Unknown tool test passed")

    @pytest.mark.asyncio
    async def test_tool_timeout_handling(self, server: DoclingMCPServer) -> None:
        """Test tool execution timeout handling."""
        call_tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[CallToolResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        # Mock a tool that takes too long
        with patch.object(server, 'execute_tool', side_effect=asyncio.TimeoutError):
            result: CallToolResult = await call_tool_handler("health_check", {})
            
            assert result.isError is True
            assert "timed out" in result.content[0].text.lower()
        
        logger.info("✓ Tool timeout handling test passed")

    @pytest.mark.asyncio
    async def test_custom_sse_handler_creation(self, server: DoclingMCPServer) -> None:
        """Test custom SSE handler creation."""
        # Create a mock SSE transport
        mock_transport: Mock = Mock()
        
        # Create custom SSE handler
        handler: Callable[[Any], Awaitable[Any]] = create_custom_sse_handler(mock_transport, server)
        
        assert callable(handler)
        assert handler.__name__ == 'custom_sse_handler'
        
        logger.info("✓ Custom SSE handler creation test passed")

    @pytest.mark.asyncio
    async def test_custom_sse_handler_request_handling(self, server: DoclingMCPServer) -> None:
        """Test custom SSE handler request processing."""
        # Create a mock request
        mock_request: Mock = Mock()
        mock_request.remote = "127.0.0.1"
        
        # Create a mock response
        mock_response: Mock = Mock()
        mock_response.prepare = AsyncMock()
        mock_response.write = AsyncMock()
        mock_response.write_eof = AsyncMock()
        
        # Mock the request to return our mock response
        mock_request.return_value = mock_response
        
        # Create SSE transport and handler
        mock_transport: Mock = Mock()
        handler: Callable[[Any], Awaitable[Any]] = create_custom_sse_handler(mock_transport, server)
        
        # Test handler execution (this will run the SSE loop)
        # We'll mock the asyncio.sleep to break the loop
        with patch('asyncio.sleep', side_effect=asyncio.CancelledError):
            try:
                result: Any = await handler(mock_request)
                # Should handle the cancellation gracefully
            except asyncio.CancelledError:
                pass  # Expected
        
        logger.info("✓ Custom SSE handler request handling test passed")

    @pytest.mark.asyncio
    async def test_error_handling_in_tool_execution(self, server: DoclingMCPServer) -> None:
        """Test error handling in tool execution."""
        call_tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[CallToolResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        # Mock execute_tool to raise an exception
        with patch.object(server, 'execute_tool', side_effect=Exception("Test error")):
            result: CallToolResult = await call_tool_handler("health_check", {})
            
            assert result.isError is True
            assert "test error" in result.content[0].text.lower()
        
        logger.info("✓ Error handling in tool execution test passed")

    @pytest.mark.asyncio
    async def test_mcp_protocol_compliance_tool_listing(self, server: DoclingMCPServer) -> None:
        """Test MCP protocol compliance for tool listing."""
        list_tools_handler: Optional[Callable[[], Awaitable[ListToolsResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'list_tools':
                list_tools_handler = handler
                break
        
        result: ListToolsResult = await list_tools_handler()
        
        # Check MCP protocol compliance
        assert hasattr(result, 'tools')
        for tool in result.tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            assert isinstance(tool.inputSchema, dict)
            assert tool.inputSchema.get('type') == 'object'
        
        logger.info("✓ MCP protocol compliance tool listing test passed")

    @pytest.mark.asyncio
    async def test_mcp_protocol_compliance_tool_call(self, server: DoclingMCPServer) -> None:
        """Test MCP protocol compliance for tool calls."""
        call_tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[CallToolResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        result: CallToolResult = await call_tool_handler("health_check", {})
        
        # Check MCP protocol compliance
        assert hasattr(result, 'content')
        assert hasattr(result, 'isError')
        assert isinstance(result.content, list)
        assert len(result.content) > 0
        
        for content in result.content:
            assert hasattr(content, 'type')
            assert content.type == 'text'
            assert hasattr(content, 'text')
        
        logger.info("✓ MCP protocol compliance tool call test passed")

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, server: DoclingMCPServer) -> None:
        """Test concurrent tool execution."""
        call_tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[CallToolResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        # Execute multiple health checks concurrently
        tasks: List[Awaitable[CallToolResult]] = []
        for i in range(5):
            task: Awaitable[CallToolResult] = call_tool_handler("health_check", {})
            tasks.append(task)
        
        results: List[CallToolResult] = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 5
        for result in results:
            assert hasattr(result, 'content')
            assert len(result.content) == 1
            assert "healthy" in result.content[0].text.lower()
        
        logger.info("✓ Concurrent tool execution test passed")

    @pytest.mark.asyncio
    async def test_tool_validation(self, server: DoclingMCPServer) -> None:
        """Test tool input validation."""
        call_tool_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[CallToolResult]]] = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        # Test with invalid tool name (None)
        result: CallToolResult = await call_tool_handler(None, {})
        
        assert result.isError is True
        assert "tool name is required" in result.content[0].text.lower()
        
        logger.info("✓ Tool validation test passed")


class TestDoclingMCPDockerIntegration:
    """Docker integration tests for Docling MCP Server."""

    @pytest.mark.asyncio
    async def test_docker_health_check(self) -> None:
        """Test Docker health check endpoint."""
        # This test assumes the Docker container is running
        # In a real CI/CD environment, this would be orchestrated
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:3020/health") as response:
                    assert response.status == 200
                    text: str = await response.text()
                    assert text == "OK"
            
            logger.info("✓ Docker health check test passed")
        except aiohttp.ClientError as e:
            pytest.skip(f"Docker container not available: {e}")

    @pytest.mark.asyncio
    async def test_docker_sse_endpoint(self) -> None:
        """Test Docker SSE endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                headers: Dict[str, str] = {"Accept": "text/event-stream"}
                async with session.get("http://localhost:3020/mcp", headers=headers) as response:
                    assert response.status == 200
                    assert response.headers.get('Content-Type') == 'text/event-stream'
            
            logger.info("✓ Docker SSE endpoint test passed")
        except aiohttp.ClientError as e:
            pytest.skip(f"Docker container not available: {e}")

    @pytest.mark.asyncio
    async def test_docker_cors_headers(self) -> None:
        """Test Docker CORS headers."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.options("http://localhost:3020/mcp") as response:
                    assert response.status == 200
                    assert response.headers.get('Access-Control-Allow-Origin') == '*'
                    assert 'GET' in response.headers.get('Access-Control-Allow-Methods', '')
            
            logger.info("✓ Docker CORS headers test passed")
        except aiohttp.ClientError as e:
            pytest.skip(f"Docker container not available: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])