#!/usr/bin/env python3
"""
Docling MCP Server - Fixed with Official MCP Patterns

This server provides document processing capabilities through the Model Context Protocol (MCP)
using official implementation patterns from the MCP specification.
"""

import asyncio
import json
import logging
import os
import sys
import traceback
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

# MCP imports
try:
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
    )
    import mcp.server.stdio
    from aiohttp import web
except ImportError as e:
    print(f"Error importing MCP modules: {e}")
    print("Please install MCP SDK: pip install mcp")
    sys.exit(1)

# Configure logging with official pattern
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("docling-mcp")

# Docling imports
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PipelineOptions
    from docling.datamodel.settings import settings
    DOCLING_AVAILABLE = True
    logger.info("Docling imports successful")
except ImportError as e:
    logger.warning(f"Docling not available: {e}")
    DOCLING_AVAILABLE = False

class DoclingMCPServer:
    """Docling MCP Server with official implementation patterns."""
    
    def __init__(self, name: str = "docling-mcp"):
        """Initialize server with proper capabilities following official pattern."""
        self.server = Server(name)
        self.capabilities = None  # Will be set during initialization
        self.setup_handlers()
        logger.info(f"Docling MCP Server '{name}' initialized")
    
    def setup_handlers(self):
        """Setup MCP server handlers following official patterns."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available document processing tools - official pattern."""
            tools = []
            
            if DOCILING_AVAILABLE:
                tools.append(Tool(
                    name="convert_document",
                    description="Convert documents to structured format using Docling",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the document file"
                            },
                            "output_format": {
                                "type": "string",
                                "description": "Output format (markdown, text, json)",
                                "enum": ["markdown", "text", "json"],
                                "default": "markdown"
                            }
                        },
                        "required": ["file_path"],
                        "additionalProperties": False
                    }
                ))
                
                tools.append(Tool(
                    name="process_documents_batch",
                    description="Process multiple documents in batch",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_paths": {
                                "type": "array",
                                "description": "List of document file paths",
                                "items": {"type": "string"}
                            },
                            "output_format": {
                                "type": "string",
                                "description": "Output format for all documents",
                                "enum": ["markdown", "text", "json"],
                                "default": "markdown"
                            }
                        },
                        "required": ["file_paths"],
                        "additionalProperties": False
                    }
                ))
            
            tools.append(Tool(
                name="health_check",
                description="Check server health and capabilities",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ))
            
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls with comprehensive error handling - official pattern."""
            try:
                # Validate tool name
                if not name:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Error: Tool name is required")],
                        isError=True
                    )
                
                # Execute tool with timeout per specification
                result = await asyncio.wait_for(
                    self.execute_tool(name, arguments or {}),
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
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute specific tool with proper error handling."""
        logger.info(f"Executing tool: {name} with arguments: {arguments}")
        
        if name == "health_check":
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Docling MCP Server is healthy. Docling available: {DOCILING_AVAILABLE}"
                )]
            )
        
        if not DOCILING_AVAILABLE:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="Error: Docling is not available. Please install docling: pip install docling"
                )],
                isError=True
            )
        
        if name == "convert_document":
            return await self.convert_document(arguments)
        elif name == "process_documents_batch":
            return await self.process_documents_batch(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )
    
    async def convert_document(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Convert a single document using Docling."""
        file_path = arguments.get("file_path")
        output_format = arguments.get("output_format", "markdown")
        
        if not file_path:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: file_path is required")],
                isError=True
            )
        
        if not os.path.exists(file_path):
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: File not found: {file_path}")],
                isError=True
            )
        
        try:
            converter = DocumentConverter()
            result = converter.convert(file_path)
            
            if output_format == "markdown":
                content = result.document.export_to_markdown()
            elif output_format == "text":
                content = result.document.export_to_text()
            elif output_format == "json":
                content = json.dumps(result.document.export_to_dict(), indent=2)
            else:
                content = result.document.export_to_markdown()
            
            return CallToolResult(
                content=[TextContent(type="text", text=content)]
            )
            
        except Exception as e:
            logger.error(f"Document conversion error: {e}", exc_info=True)
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error converting document: {str(e)}")],
                isError=True
            )
    
    async def process_documents_batch(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Process multiple documents in batch."""
        file_paths = arguments.get("file_paths", [])
        output_format = arguments.get("output_format", "markdown")
        
        if not file_paths:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: file_paths is required")],
                isError=True
            )
        
        results = []
        errors = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                errors.append(f"File not found: {file_path}")
                continue
            
            try:
                converter = DocumentConverter()
                result = converter.convert(file_path)
                
                if output_format == "markdown":
                    content = result.document.export_to_markdown()
                elif output_format == "text":
                    content = result.document.export_to_text()
                elif output_format == "json":
                    content = json.dumps(result.document.export_to_dict(), indent=2)
                else:
                    content = result.document.export_to_markdown()
                
                results.append(f"=== {file_path} ===\n{content}")
                
            except Exception as e:
                errors.append(f"Error processing {file_path}: {str(e)}")
        
        output = []
        if results:
            output.append("\n\n".join(results))
        if errors:
            output.append("Errors:\n" + "\n".join(errors))
        
        return CallToolResult(
            content=[TextContent(type="text", text="\n\n".join(output) if output else "No results")]
        )

def create_custom_sse_handler(sse_transport, server):
    """Create a custom SSE handler for MCP SDK compatibility when official methods are missing."""
    
    async def custom_sse_handler(request):
        """Custom SSE handler that implements the official MCP SSE protocol."""
        logger.info(f"SSE connection from {request.remote}")
        
        # Prepare SSE response
        response = web.StreamResponse()
        response.headers.update({
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        })
        
        await response.prepare(request)
        
        try:
            # Create custom streams for MCP communication
            # Instead of using connect_sse(), we'll create our own stream handling
            
            # Create a simple queue-based stream system
            from asyncio import Queue
            from mcp.server.session import ServerSession
            
            # Create queues for bidirectional communication
            client_to_server_queue = Queue()
            server_to_client_queue = Queue()
            
            # Create stream objects that mimic the MCP stream interface
            class SimpleStream:
                def __init__(self, input_queue, output_queue):
                    self.input_queue = input_queue
                    self.output_queue = output_queue
                
                async def read(self):
                    return await self.input_queue.get()
                
                async def write(self, data):
                    await self.output_queue.put(data)
            
            # Create the streams
            read_stream = SimpleStream(client_to_server_queue, server_to_client_queue)
            write_stream = SimpleStream(server_to_client_queue, client_to_server_queue)
            
            # Start the MCP server session in the background
            session_task = asyncio.create_task(
                server.server.run(
                    read_stream,
                    write_stream,
                    server.server.create_initialization_options()
                )
            )
            
            # Handle SSE events
            while True:
                try:
                    # Check for data to send to client
                    if not server_to_client_queue.empty():
                        data = await server_to_client_queue.get()
                        # Format as SSE event
                        sse_data = f"data: {json.dumps(data)}\n\n"
                        await response.write(sse_data.encode('utf-8'))
                    
                    # Send keepalive every 30 seconds
                    await asyncio.sleep(0.1)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"SSE handling error: {e}")
                    break
            
            # Clean up
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

async def run_stdio_server(server: DoclingMCPServer):
    """Official STDIO transport implementation following official pattern."""
    logger.info("Starting Docling MCP Server with STDIO transport...")
    
    try:
        # Use context manager for proper cleanup - official pattern
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
        logger.error(traceback.format_exc())
        raise

async def run_http_server(server: DoclingMCPServer, host: str = "0.0.0.0", port: int = 3020):
    """Official HTTP transport implementation with SSE following official pattern."""
    logger.info(f"Starting Docling MCP Server with HTTP transport on {host}:{port}...")
    
    try:
        # Create aiohttp application
        app = web.Application()
        
        # Create SSE transport with proper configuration - official pattern
        # Use relative path for the transport endpoint (MCP SDK 1.21.0+ requirement)
        sse_transport = SseServerTransport("/mcp")
        
        # Handle MCP sessions - official pattern
        async def handle_session(session_streams):
            """Handle MCP sessions with proper error handling and logging."""
            read_stream, write_stream = session_streams
            try:
                await server.server.run(
                    read_stream,
                    write_stream,
                    server.server.create_initialization_options()
                )
            except Exception as e:
                logger.error(f"Session handling error: {e}", exc_info=True)
                raise
        
        # Set up session handler for SSE transport - official pattern
        sse_transport.handle_session = handle_session
        
        # Add SSE endpoint using the correct method - official pattern
        # In MCP SDK 1.21.0+, we need to handle the method name properly
        try:
            # Try the official method name first
            app.router.add_get("/mcp", sse_transport.handle_request)
        except AttributeError:
            # Fallback to alternative method names or custom implementation
            logger.warning("SseServerTransport.handle_request not found, trying alternative methods")
            
            # Check for alternative method names
            if hasattr(sse_transport, 'handle_sse_request'):
                app.router.add_get("/mcp", sse_transport.handle_sse_request)
            elif hasattr(sse_transport, 'sse_handler'):
                app.router.add_get("/mcp", sse_transport.sse_handler)
            elif hasattr(sse_transport, 'handle'):
                app.router.add_get("/mcp", sse_transport.handle)
            else:
                # If none of the expected methods exist, implement custom SSE handler
                logger.info("Implementing custom SSE handler for MCP SDK compatibility")
                app.router.add_get("/mcp", create_custom_sse_handler(sse_transport, server))
        
        # Add health check endpoint
        async def health_check(request):
            """Health check endpoint for monitoring."""
            return web.Response(text="OK", status=200)
        app.router.add_get("/health", health_check)
        
        # Configure CORS for browser clients - official pattern
        async def handle_cors_options(request):
            """Handle CORS preflight requests."""
            return web.Response(
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Accept, Cache-Control",
                    "Access-Control-Max-Age": "86400",  # 24 hours
                }
            )
        
        app.router.add_options("/mcp", handle_cors_options)
        
        # Start server with proper session handling
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"HTTP server started on {host}:{port}")
        logger.info(f"SSE endpoint available at http://{host}:{port}/mcp")
        logger.info(f"Health check available at http://{host}:{port}/health")
        
        # Keep server running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        finally:
            await runner.cleanup()
        
    except Exception as e:
        logger.error(f"Error running HTTP server: {e}")
        logger.error(traceback.format_exc())
        raise

def main():
    """Main entry point with proper argument parsing."""
    parser = argparse.ArgumentParser(description="Docling MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport type to use"
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
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create server
    server = DoclingMCPServer("docling-mcp")
    
    # Run with appropriate transport
    try:
        if args.transport == "stdio":
            asyncio.run(run_stdio_server(server))
        elif args.transport == "http":
            asyncio.run(run_http_server(server, args.host, args.port))
        else:
            logger.error(f"Unknown transport: {args.transport}")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()