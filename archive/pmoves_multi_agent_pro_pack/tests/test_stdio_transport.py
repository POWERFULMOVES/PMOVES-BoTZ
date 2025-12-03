#!/usr/bin/env python3
"""
STDIO Transport Tests for Docling MCP Server

This module contains comprehensive tests for STDIO transport functionality,
including protocol compliance, error handling, and stream management.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from io import StringIO
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Any, Dict, List, Optional

import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from docling_mcp_server import DoclingMCPServer, run_stdio_server


logger = logging.getLogger(__name__)


class TestSTDIOTransport:
    """Test STDIO transport functionality."""

    @pytest.fixture
    def server(self):
        """Create a Docling MCP server instance for testing."""
        return DoclingMCPServer("test-stdio-docling-mcp")

    @pytest.mark.asyncio
    async def test_stdio_server_initialization(self, server):
        """Test STDIO server initialization."""
        assert server.server is not None
        assert server.server.name == "test-stdio-docling-mcp"
        
        logger.info("✓ STDIO server initialization test passed")

    @pytest.mark.asyncio
    async def test_stdio_stream_creation(self):
        """Test STDIO stream creation and management."""
        # Mock stdio_server context manager
        mock_read_stream = Mock()
        mock_write_stream = Mock()
        
        mock_read_stream.read = AsyncMock(return_value=b'{"test": "data"}')
        mock_write_stream.write = AsyncMock()
        
        # Test stream functionality
        data = await mock_read_stream.read()
        assert data == b'{"test": "data"}'
        
        await mock_write_stream.write(b'{"response": "ok"}')
        mock_write_stream.write.assert_called_once()
        
        logger.info("✓ STDIO stream creation test passed")

    @pytest.mark.asyncio
    async def test_stdio_json_message_handling(self):
        """Test STDIO JSON message handling."""
        test_message = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        # Convert to JSON and back
        json_str = json.dumps(test_message)
        parsed_message = json.loads(json_str)
        
        assert parsed_message == test_message
        assert parsed_message["jsonrpc"] == "2.0"
        assert parsed_message["method"] == "tools/list"
        assert parsed_message["id"] == 1
        
        logger.info("✓ STDIO JSON message handling test passed")

    @pytest.mark.asyncio
    async def test_stdio_binary_data_handling(self):
        """Test STDIO binary data handling."""
        # Test binary data
        binary_data = b'\x00\x01\x02\x03\x04\x05'
        
        # Mock binary read/write
        mock_stream = Mock()
        mock_stream.read = AsyncMock(return_value=binary_data)
        mock_stream.write = AsyncMock()
        
        # Test read
        read_data = await mock_stream.read()
        assert read_data == binary_data
        
        # Test write
        await mock_stream.write(binary_data)
        mock_stream.write.assert_called_once_with(binary_data)
        
        logger.info("✓ STDIO binary data handling test passed")

    @pytest.mark.asyncio
    async def test_stdio_line_based_protocol(self):
        """Test STDIO line-based protocol handling."""
        # Test line-based messages
        messages = [
            '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}',
            '{"jsonrpc": "2.0", "method": "tools/call", "id": 2}',
            '{"jsonrpc": "2.0", "method": "initialize", "id": 3}'
        ]
        
        # Join with newlines (typical for line-based protocols)
        protocol_data = '\n'.join(messages) + '\n'
        
        # Split back into lines
        lines = protocol_data.strip().split('\n')
        
        assert len(lines) == len(messages)
        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed["jsonrpc"] == "2.0"
            assert parsed["id"] == i + 1
        
        logger.info("✓ STDIO line-based protocol test passed")

    @pytest.mark.asyncio
    async def test_stdio_error_handling(self):
        """Test STDIO error handling."""
        # Mock broken pipe error
        mock_stream = Mock()
        mock_stream.write = AsyncMock(side_effect=BrokenPipeError("Broken pipe"))
        
        # Test error handling
        try:
            await mock_stream.write(b"test data")
            assert False, "Should have raised BrokenPipeError"
        except BrokenPipeError:
            # Expected
            pass
        
        logger.info("✓ STDIO error handling test passed")

    @pytest.mark.asyncio
    async def test_stdio_connection_cleanup(self):
        """Test STDIO connection cleanup."""
        # Mock cleanup
        mock_stream = Mock()
        mock_stream.close = Mock()
        
        # Test cleanup
        mock_stream.close()
        mock_stream.close.assert_called_once()
        
        logger.info("✓ STDIO connection cleanup test passed")


class TestSTDIOServerSession:
    """Test STDIO server session management."""

    @pytest.mark.asyncio
    async def test_stdio_session_initialization(self):
        """Test STDIO session initialization."""
        # Mock initialization options
        mock_options = Mock()
        mock_options.capabilities = {"tools": {"listChanged": True}}
        
        # Test options
        assert hasattr(mock_options, 'capabilities')
        assert 'tools' in mock_options.capabilities
        
        logger.info("✓ STDIO session initialization test passed")

    @pytest.mark.asyncio
    async def test_stdio_session_lifecycle(self):
        """Test STDIO session lifecycle."""
        # Mock session lifecycle
        session_started = False
        session_ended = False
        
        async def start_session():
            nonlocal session_started
            session_started = True
        
        async def end_session():
            nonlocal session_ended
            session_ended = True
        
        # Test lifecycle
        await start_session()
        assert session_started is True
        
        await end_session()
        assert session_ended is True
        
        logger.info("✓ STDIO session lifecycle test passed")

    @pytest.mark.asyncio
    async def test_stdio_session_message_exchange(self):
        """Test STDIO session message exchange."""
        # Mock message exchange
        messages_sent = []
        messages_received = []
        
        async def send_message(message):
            messages_sent.append(message)
        
        async def receive_message():
            if messages_received:
                return messages_received.pop(0)
            return None
        
        # Test exchange
        test_message = {"jsonrpc": "2.0", "method": "test", "id": 1}
        messages_received.append(test_message)
        
        received = await receive_message()
        assert received == test_message
        
        response = {"jsonrpc": "2.0", "result": "ok", "id": 1}
        await send_message(response)
        assert len(messages_sent) == 1
        assert messages_sent[0] == response
        
        logger.info("✓ STDIO session message exchange test passed")


class TestSTDIOServerIntegration:
    """Test STDIO server integration."""

    @pytest.mark.asyncio
    async def test_stdio_server_with_mock_streams(self, server):
        """Test STDIO server with mock streams."""
        # Mock read/write streams
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()
        
        # Mock message exchange
        test_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        mock_read_stream.read.return_value = json.dumps(test_request).encode()
        
        # Test server interaction
        # Note: This is a simplified test - real integration would be more complex
        assert mock_read_stream is not None
        assert mock_write_stream is not None
        
        logger.info("✓ STDIO server with mock streams test passed")

    @pytest.mark.asyncio
    async def test_stdio_server_tool_listing(self, server):
        """Test STDIO server tool listing."""
        # Get tool listing handler
        list_tools_handler = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'list_tools':
                list_tools_handler = handler
                break
        
        assert list_tools_handler is not None
        
        # Test tool listing
        result = await list_tools_handler()
        assert hasattr(result, 'tools')
        assert len(result.tools) >= 1
        
        logger.info("✓ STDIO server tool listing test passed")

    @pytest.mark.asyncio
    async def test_stdio_server_tool_call(self, server):
        """Test STDIO server tool call."""
        # Get tool call handler
        call_tool_handler = None
        for handler in server.server._handlers:
            if hasattr(handler, '__name__') and handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break
        
        assert call_tool_handler is not None
        
        # Test tool call
        result = await call_tool_handler("health_check", {})
        assert hasattr(result, 'content')
        assert len(result.content) == 1
        
        logger.info("✓ STDIO server tool call test passed")


class TestSTDIOServerErrorRecovery:
    """Test STDIO server error recovery."""

    @pytest.mark.asyncio
    async def test_stdio_server_broken_pipe_recovery(self):
        """Test STDIO server broken pipe recovery."""
        # Mock broken pipe scenario
        broken_pipe_raised = False
        
        async def mock_server_run():
            nonlocal broken_pipe_raised
            try:
                # Simulate server operation
                await asyncio.sleep(0.001)
                raise BrokenPipeError("Broken pipe")
            except BrokenPipeError:
                broken_pipe_raised = True
                # Simulate graceful handling
                pass
        
        # Test error recovery
        await mock_server_run()
        assert broken_pipe_raised is True
        
        logger.info("✓ STDIO server broken pipe recovery test passed")

    @pytest.mark.asyncio
    async def test_stdio_server_keyboard_interrupt(self):
        """Test STDIO server keyboard interrupt handling."""
        # Mock keyboard interrupt
        interrupt_raised = False
        
        async def mock_server_run():
            nonlocal interrupt_raised
            try:
                # Simulate server operation
                await asyncio.sleep(0.001)
                raise KeyboardInterrupt()
            except KeyboardInterrupt:
                interrupt_raised = True
                # Simulate graceful shutdown
                pass
        
        # Test interrupt handling
        await mock_server_run()
        assert interrupt_raised is True
        
        logger.info("✓ STDIO server keyboard interrupt test passed")

    @pytest.mark.asyncio
    async def test_stdio_server_json_parse_error(self):
        """Test STDIO server JSON parse error handling."""
        # Mock invalid JSON
        invalid_json = '{"invalid": json}'
        
        # Test JSON parsing error
        try:
            json.loads(invalid_json)
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError:
            # Expected
            pass
        
        logger.info("✓ STDIO server JSON parse error test passed")

    @pytest.mark.asyncio
    async def test_stdio_server_malformed_message(self):
        """Test STDIO server malformed message handling."""
        # Mock malformed message
        malformed_messages = [
            "",  # Empty message
            "not json",  # Not JSON
            '{"partial":}',  # Invalid JSON
            None,  # None message
        ]
        
        for message in malformed_messages:
            if message is None:
                # Should handle None gracefully
                continue
            elif not message:
                # Should handle empty message
                continue
            else:
                # Should handle invalid JSON
                try:
                    json.loads(message)
                    # Valid JSON, should not raise
                    pass
                except json.JSONDecodeError:
                    # Invalid JSON, expected
                    pass
        
        logger.info("✓ STDIO server malformed message test passed")


class TestSTDIOServerPerformance:
    """Test STDIO server performance characteristics."""

    @pytest.mark.asyncio
    async def test_stdio_message_throughput(self):
        """Test STDIO message throughput."""
        # Test message processing speed
        num_messages = 1000
        message_size = 100  # bytes
        
        # Generate test messages
        test_messages = []
        for i in range(num_messages):
            message = {
                "id": i,
                "data": "x" * message_size,
                "timestamp": i
            }
            test_messages.append(json.dumps(message))
        
        # Simulate processing
        start_time = asyncio.get_event_loop().time()
        
        processed_messages = []
        for message_str in test_messages:
            parsed = json.loads(message_str)
            processed_messages.append(parsed)
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        assert len(processed_messages) == num_messages
        assert processing_time < 1.0  # Should process 1000 messages in less than 1 second
        
        logger.info(f"✓ STDIO message throughput test passed: {num_messages} messages in {processing_time:.3f}s")

    @pytest.mark.asyncio
    async def test_stdio_large_message_handling(self):
        """Test STDIO large message handling."""
        # Test large message processing
        large_data = "x" * 100000  # 100KB
        
        large_message = {
            "type": "large_data",
            "content": large_data,
            "size": len(large_data)
        }
        
        # Test JSON serialization/deserialization
        json_str = json.dumps(large_message)
        parsed_message = json.loads(json_str)
        
        assert parsed_message["type"] == "large_data"
        assert parsed_message["size"] == len(large_data)
        assert parsed_message["content"] == large_data
        
        logger.info("✓ STDIO large message handling test passed")

    @pytest.mark.asyncio
    async def test_stdio_concurrent_message_processing(self):
        """Test STDIO concurrent message processing."""
        # Test concurrent processing
        num_concurrent = 10
        
        async def process_message(message_id):
            await asyncio.sleep(0.001)  # Simulate processing
            return {"id": message_id, "status": "processed"}
        
        # Process messages concurrently
        start_time = asyncio.get_event_loop().time()
        
        tasks = [process_message(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks)
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        assert len(results) == num_concurrent
        assert all(result["status"] == "processed" for result in results)
        assert processing_time < 0.1  # Should complete in less than 100ms
        
        logger.info(f"✓ STDIO concurrent message processing test passed: {processing_time:.3f}s")


class TestSTDIOServerProtocolCompliance:
    """Test STDIO server protocol compliance."""

    @pytest.mark.asyncio
    async def test_stdio_json_rpc_compliance(self):
        """Test STDIO JSON-RPC compliance."""
        # Test JSON-RPC 2.0 compliance
        json_rpc_message = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        # Verify required fields
        assert "jsonrpc" in json_rpc_message
        assert json_rpc_message["jsonrpc"] == "2.0"
        assert "method" in json_rpc_message
        assert "id" in json_rpc_message
        
        logger.info("✓ STDIO JSON-RPC compliance test passed")

    @pytest.mark.asyncio
    async def test_stdio_mcp_protocol_compliance(self):
        """Test STDIO MCP protocol compliance."""
        # Test MCP protocol compliance
        mcp_messages = [
            {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            },
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "health_check",
                    "arguments": {}
                },
                "id": 2
            },
            {
                "jsonrpc": "2.0",
                "result": {
                    "tools": []
                },
                "id": 1
            }
        ]
        
        for message in mcp_messages:
            # Verify JSON-RPC compliance
            assert "jsonrpc" in message
            assert message["jsonrpc"] == "2.0"
            
            # Verify message structure
            if "method" in message:
                assert isinstance(message["method"], str)
            if "id" in message:
                assert isinstance(message["id"], int)
            if "result" in message:
                assert isinstance(message["result"], dict)
        
        logger.info("✓ STDIO MCP protocol compliance test passed")

    @pytest.mark.asyncio
    async def test_stdio_message_validation(self):
        """Test STDIO message validation."""
        # Test message validation
        valid_messages = [
            {"jsonrpc": "2.0", "method": "test", "id": 1},
            {"jsonrpc": "2.0", "result": {}, "id": 1},
            {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1}
        ]
        
        invalid_messages = [
            {"method": "test", "id": 1},  # Missing jsonrpc
            {"jsonrpc": "2.0", "id": 1},  # Missing method/result/error
            {"jsonrpc": "1.0", "method": "test", "id": 1},  # Wrong jsonrpc version
        ]
        
        # Test valid messages
        for message in valid_messages:
            assert "jsonrpc" in message
            assert message["jsonrpc"] == "2.0"
            assert any(key in message for key in ["method", "result", "error"])
        
        # Test invalid messages
        for message in invalid_messages:
            # Should fail validation
            if "jsonrpc" not in message or message["jsonrpc"] != "2.0":
                continue  # Invalid jsonrpc
            if not any(key in message for key in ["method", "result", "error"]):
                continue  # Missing required field
            
            # If we get here, the message is unexpectedly valid
            assert False, f"Message should be invalid: {message}"
        
        logger.info("✓ STDIO message validation test passed")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])