#!/usr/bin/env python3
"""
Docling MCP Python Client - Basic Example

This example demonstrates basic usage of the Docling MCP service from Python.
It includes connection management, tool calling, and error handling.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

import aiohttp
import sseclient


class OutputFormat(Enum):
    """Supported output formats."""
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"


@dataclass
class MCPConfig:
    """Configuration for MCP client."""
    server_url: str = "http://localhost:3020/mcp"
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    max_connections: int = 10
    enable_logging: bool = True


class DoclingMCPClient:
    """Docling MCP Client with comprehensive features."""
    
    def __init__(self, config: MCPConfig = None):
        self.config = config or MCPConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        self.request_id = 0
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.metrics = {
            'connections': 0,
            'requests': 0,
            'errors': 0,
            'response_times': []
        }
        
        # Setup logging
        if self.config.enable_logging:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        self.logger = logging.getLogger(__name__)
    
    async def connect(self) -> bool:
        """Connect to the MCP server."""
        try:
            self.logger.info(f"Connecting to MCP server at {self.config.server_url}")
            
            # Create session with connection pooling
            connector = aiohttp.TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=self.config.max_connections
            )
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
            
            # Test connection with health check
            health = await self.health_check()
            if health:
                self.is_connected = True
                self.metrics['connections'] += 1
                self.logger.info("Successfully connected to MCP server")
                return True
            else:
                self.logger.error("Health check failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.metrics['errors'] += 1
            return False
    
    async def disconnect(self):
        """Disconnect from the server."""
        if self.session:
            await self.session.close()
            self.session = None
            self.is_connected = False
            self.logger.info("Disconnected from MCP server")
    
    async def _make_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the MCP server."""
        if not self.is_connected:
            raise ConnectionError("Not connected to server")
        
        self.request_id += 1
        request_id = str(self.request_id)
        
        # Create request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        try:
            start_time = time.time()
            self.metrics['requests'] += 1
            
            # Note: This is a simplified implementation
            # In a real implementation, you'd need to handle SSE properly
            # For now, we'll use HTTP POST to the MCP gateway
            
            if self.session:
                async with self.session.post(
                    self.config.server_url.replace('/mcp', '/tools/call'),
                    json=request
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_time = (time.time() - start_time) * 1000
                        self.metrics['response_times'].append(response_time)
                        return result
                    else:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")
            else:
                raise ConnectionError("No active session")
                
        except Exception as e:
            self.metrics['errors'] += 1
            self.logger.error(f"Request failed: {e}")
            raise
        finally:
            self.pending_requests.pop(request_id, None)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        result = await self._make_request("tools/list", {})
        return result.get('tools', [])
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a specific tool."""
        params = {
            "name": tool_name,
            "arguments": arguments or {}
        }
        return await self._make_request("tools/call", params)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            return await self.call_tool("health_check")
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def get_config(self) -> Dict[str, Any]:
        """Get server configuration."""
        return await self.call_tool("get_config")
    
    async def convert_document(self, file_path: str, output_format: OutputFormat = OutputFormat.MARKDOWN) -> str:
        """Convert a document to the specified format."""
        result = await self.call_tool("convert_document", {
            "file_path": file_path,
            "output_format": output_format.value
        })
        
        # Extract content from result
        if isinstance(result, dict) and 'content' in result:
            content = result['content']
            if isinstance(content, list) and len(content) > 0:
                return content[0].get('text', '')
            elif isinstance(content, str):
                return content
        
        return str(result)
    
    async def process_batch(self, file_paths: List[str], output_format: OutputFormat = OutputFormat.MARKDOWN) -> str:
        """Process multiple documents in batch."""
        result = await self.call_tool("process_documents_batch", {
            "file_paths": file_paths,
            "output_format": output_format.value
        })
        
        # Extract content from result
        if isinstance(result, dict) and 'content' in result:
            content = result['content']
            if isinstance(content, list) and len(content) > 0:
                return content[0].get('text', '')
            elif isinstance(content, str):
                return content
        
        return str(result)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics."""
        avg_response_time = (
            sum(self.metrics['response_times']) / len(self.metrics['response_times'])
            if self.metrics['response_times'] else 0
        )
        
        return {
            'connections': self.metrics['connections'],
            'requests': self.metrics['requests'],
            'errors': self.metrics['errors'],
            'avg_response_time_ms': round(avg_response_time, 2),
            'response_time_count': len(self.metrics['response_times'])
        }
    
    def reset_metrics(self):
        """Reset metrics."""
        self.metrics = {
            'connections': 0,
            'requests': 0,
            'errors': 0,
            'response_times': []
        }


async def main():
    """Main example function."""
    # Configure client
    config = MCPConfig(
        server_url="http://localhost:3020/mcp",
        timeout=30.0,
        retry_attempts=3,
        retry_delay=1.0
    )
    
    client = DoclingMCPClient(config)
    
    try:
        # Connect to server
        print("Connecting to Docling MCP server...")
        connected = await client.connect()
        
        if not connected:
            print("Failed to connect to server")
            return
        
        # Health check
        print("\nPerforming health check...")
        health = await client.health_check()
        print(f"Health status: {json.dumps(health, indent=2)}")
        
        # List available tools
        print("\nListing available tools...")
        tools = await client.list_tools()
        print(f"Available tools: {json.dumps(tools, indent=2)}")
        
        # Get server configuration
        print("\nGetting server configuration...")
        config = await client.get_config()
        print(f"Server config: {json.dumps(config, indent=2)}")
        
        # Example: Convert a document (you'll need actual files)
        # print("\nConverting document...")
        # result = await client.convert_document('/path/to/document.pdf', OutputFormat.MARKDOWN)
        # print(f"Conversion result: {result[:200]}...")
        
        # Get metrics
        print("\nClient metrics:")
        metrics = client.get_metrics()
        print(json.dumps(metrics, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.disconnect()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())